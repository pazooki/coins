import sys
import time
import ta
import numpy as np
import pandas as pd
import pandas_ta as pta
import talib

from decimal import Decimal
from binance.enums import *

from strategies.strategy import Strategy, Position, POS_INIT
from utils import find_nearest_price, get_ema_slope_degrees, filters_to_signals, truncate


BTCUSDT = 'BTCUSDT'


class DarkSteps(Strategy):
    SIGNAL_THRESHOLD = 3

    ORDERS_MAX_TRIES = 30

    BALANCE_MIN_BTC = Decimal('0.0001')
    BALANCE_MIN_USDT = Decimal('5.0')

    RSI_PERIOD = 14
    RSI_HIGH_THRESHOLD = 70
    RSI_LOW_THRESHOLD = 30

    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9

    EMA_SHORT_LENGTH = 5
    EMA_LONG_LENGTH = 40
    EMA_SLOPE_PERIOD = 5
    EMA_LOW_THRESHOLD = -0.2
    EMA_HIGH_THRESHOLD = 0.2


    BB_PERIOD = 20
    BB_STD_FACTOR = 2

    _BTC_QTY_PRECISION = '%.5f'

    def __init__(
            self, 
            rest_client, 
            testing=True,
            is_isolated_margin=False,
            is_cross_margin=False,
            leverage=1,
            warm_up_threshold=50, 
            fees_pct=Decimal('0.10'), 
            stop_loss_pct=Decimal('0.1'),
            take_profit_pct=Decimal('0.1'),
            # model_rfr,
            trades_history=None
        ):
        super().__init__(
            rest_client, 
            testing=testing, 
            is_isolated_margin=is_isolated_margin,
            is_cross_margin=is_cross_margin,
            leverage=leverage, 
            warm_up_threshold=warm_up_threshold, 
            fees_pct=fees_pct, 
            stop_loss_pct=stop_loss_pct, 
            take_profit_pct=take_profit_pct,
            trades_history=trades_history
        )
        # self.model_rfr = model_rfr
        self.is_first_order = True

    def update_indicators(self):
        self.ema_short = pta.ema(self.dataset.price, length=self.EMA_SHORT_LENGTH, overlay=True)
        self.ema_long = pta.ema(self.dataset.price, length=self.EMA_LONG_LENGTH, overlay=True)
        self.rsi = talib.RSI(self.dataset.price, timeperiod=self.RSI_PERIOD)
        self.bbands_upper, self.bbands_middle, self.bbands_lower = talib.BBANDS(self.dataset.price, timeperiod=self.BB_PERIOD, nbdevup=self.BB_STD_FACTOR, nbdevdn=self.BB_STD_FACTOR)
        self.macd, self.macd_signal, self.macd_hist = talib.MACD(self.dataset.price, fastperiod=self.MACD_FAST, slowperiod=self.MACD_SLOW, signalperiod=self.MACD_SIGNAL)
        


    def init_position(self):
        if self.is_first_order:
            current_price = self.current_price
            if self.balance['BTC'] > self.BALANCE_MIN_BTC:
                self.position = Position(
                    open_price=current_price, 
                    btc_qty=self.balance['BTC'], 
                    side=SIDE_BUY,
                    fees_pct=self.fees_pct
                )
            elif self.balance['USDT'] > self.BALANCE_MIN_USDT:
                self.position = Position(
                    open_price=current_price, 
                    btc_qty=self.balance['USDT'] / current_price,
                    side=SIDE_SELL,
                    fees_pct=self.fees_pct
                )
            # in case of INIT we only use current_price for both open_price and close_price
            if self.position is None:
                raise Exception('Change BALANCE_MIN_USDT and BALANCE_MIN_BTC to reflect account balance.')
            else:
                self.position.close(current_price, POS_INIT)
                print('POSITION INIT: ', self.position.__dict__)
                self.trades.append(self.position)
                self.position = None
                self.is_first_order = False


    def bid(self):
        print('ON SIDE: ', self.current_side)
        print('LAST PRICE: ', self.last_price)
        self.init_position()

        # price_mode, price_direction = self.analyze_depth()
        # print('DEPTH>   MODE: {mode}    DIRECTION: {direction:.2f}'.format(mode=price_mode, direction=price_direction))

        long_signals = filters_to_signals(self.long_condition_is_valid)
        short_signals = filters_to_signals(self.short_condition_is_valid)
        # long_signals = all(self.long_condition_is_valid)
        # short_signals = all(self.short_condition_is_valid)

        can_buy = all([
            (not self.trades or self.trades[-1].side == SIDE_SELL),
            self.balance['USDT'] > self.BALANCE_MIN_USDT,
            long_signals > short_signals,
            long_signals >= self.SIGNAL_THRESHOLD,
            # price_mode in ['SUPPORT']
        ])

        can_sell = all([
            (not self.trades or self.trades[-1].side == SIDE_BUY),
            self.balance['BTC'] > self.BALANCE_MIN_BTC,
            short_signals > long_signals,
            short_signals >= self.SIGNAL_THRESHOLD,
            # price_mode in ['RESISTANCE']
        ])

        print('SIGNALS>     LONG: %s    SHORT: %s   Buy: %s  Sell: %s' % (
            str(long_signals), str(short_signals), can_buy, can_sell
        ))

        if self.position is not None:
            print(
                'POS STATUS>     POS_PL_PCT: %f%%    POS_PRICE: %f   LAST PRICE: %f  DIFF: %f' % (
                    self.position.calc_pl_pct(self.last_price),
                    self.position.open_price,
                    self.last_price,
                    self.last_price - self.position.open_price
                )
            )
            
            if self.position.side == SIDE_SELL:
                # print('pl_pct: ', self.position.calc_pl_pct(self.last_price))

                # included the fees when checking PL pct here inside calc_pl_pct.
                take_profit_trigger = self.position.calc_pl_pct(self.last_price) <= self.TAKE_PROFIT_PCT
                stop_loss_trigger = self.position.calc_pl_pct(self.last_price) >= self.STOP_LOSS_PCT
                if take_profit_trigger: #and price_direction > self.last_price and price_mode in ['RESISTANCE']:
                    print('TAKE-PROFIT - CLOSED=WIN')
                    self.position.take_profit(self.last_price)
                    self.trades.append(self.position)
                    self.position = None
                elif stop_loss_trigger: # and price_mode in ['RESISTANCE']:
                    print('STOP-LOSS - CLOSED=LOSS')
                    self.position.stop_loss(self.last_price)
                    self.trades.append(self.position)
                    self.position = None
                else:
                    print('POSITION WAITING TO REACH ENOUGH ACTION THRESHOLD.')
            elif self.position.side == SIDE_BUY:
                # print('pl_pct: ', self.position.calc_pl_pct(self.last_price))
                take_profit_trigger = self.position.calc_pl_pct(self.last_price) >= self.TAKE_PROFIT_PCT
                stop_loss_trigger = self.position.calc_pl_pct(self.last_price) <= self.STOP_LOSS_PCT
                
                if take_profit_trigger: # and not price_direction > self.last_price and price_mode in ['RESISTANCE']:
                    print('TAKE-PROFIT - CLOSED=WIN')
                    self.position.take_profit(self.last_price)
                    self.trades.append(self.position)
                    self.position = None
                elif stop_loss_trigger: # and price_direction < self.last_price:
                    print('STOP-LOSS - CLOSED=LOSS')
                    self.position.stop_loss(self.last_price)
                    self.trades.append(self.position)
                    self.position = None
                else:
                    print('POSITION WAITING TO REACH ENOUGH ACTION THRESHOLD.')
        else:
            if filters_to_signals(self.cannot_enter) > 1:
                print('WAIT TO BUY @ PROFT PCT:   %f >= %f  AND  %f <= %f' % (
                    self.trades[-1].calc_close_pl_pct(self.last_price), (-1 * (self.TAKE_PROFIT_PCT / 2)),
                    self.trades[-1].calc_close_pl_pct(self.last_price), (self.TAKE_PROFIT_PCT / 2),
                ))
                print('########## WATCHING FOR ENTRY...')
            elif any(self.can_enter):
                print('ENTRY CRITERIA: MET')
                if can_buy:
                    attempts = 0
                    while attempts < self.ORDERS_MAX_TRIES:
                        try:
                            if self.is_cross_margin:
                                self.long_all_market()
                            else:
                                self.buy_all_market()
                            break
                        except Exception as e:
                            print(e)
                            # time.sleep(0.2)
                            attempts += 1
                elif can_sell:
                    attempts = 0
                    while attempts < self.ORDERS_MAX_TRIES:
                        try:
                            if self.is_cross_margin:
                                self.short_all_market()
                            else:
                                self.sell_all_market()
                            break
                        except Exception as e:
                            print(e)
                            # time.sleep(0.2)
                            attempts += 1
                else:
                    print('Going to WAIT more')
            else:
                print('ENTRY CRITERIA: NOT MET')

    
    def long_all_market(self):
        current_price = self.current_price
        txn_fee = ((self.balance['USDT'] / current_price) * self.fees_pct)
        btc_qty = (self.balance['USDT'] / current_price) - txn_fee
        try:
            order = self.rest_client.create_margin_order(
                symbol=BTCUSDT, 
                side=SIDE_BUY, 
                type=ORDER_TYPE_MARKET, 
                isIsolated=self.is_isolated_margin, 
                quantity=self._BTC_QTY_PRECISION % btc_qty
            )
            self.orders.append(order)
            print('ORDER: ', order)

            self.position = Position(open_price=current_price, btc_qty=btc_qty, side=SIDE_BUY, fees_pct=self.fees_pct)
            print('BUY# Price: %f   Qty: %f  TXN Fee: %f' % (self.position.open_price, btc_qty, txn_fee))
            print(self.position.__dict__)
            self.init_margin_balance()
        except Exception as e:
            print(e)
            import pdb;pdb.set_trace()
    
    def short_all_market(self):
        current_price = self.current_price
        txn_fee_in_btc = self.fees_pct * self.balance['BTC']
        btc_qty = self.balance['BTC']
        try:
            order = self.rest_client.create_margin_order(
                symbol=BTCUSDT, 
                side=SIDE_SELL, 
                type=ORDER_TYPE_MARKET, 
                isIsolated=self.is_isolated_margin, 
                quantity=self._BTC_QTY_PRECISION % btc_qty
            )
            self.orders.append(order)
            print('ORDER: ', order)

            self.position = Position(open_price=current_price, btc_qty=btc_qty, side=SIDE_SELL, fees_pct=self.fees_pct)
            print('BUY# Price: %f   Qty: %f  TXN Fee: %f' % (self.position.open_price, btc_qty, txn_fee_in_btc))
            print(self.position.__dict__)
            self.init_margin_balance()
        except Exception as e:
            print(e)
            import pdb;pdb.set_trace()



    def buy_all_market(self):
        current_price = self.current_price
        
        txn_fee = self.fees_pct * self.balance__spot['USDT']
        quote_qty_order = self.balance__spot['USDT'] - txn_fee

        btc_qty = (self.balance__spot['USDT'] / current_price) - ((self.balance__spot['USDT'] / current_price) * self.fees_pct)
        print('quote_qty_order: ', quote_qty_order)

        order = self.rest_client.order_market_buy(symbol=BTCUSDT, quoteOrderQty='%.2f' % quote_qty_order)

        self.position = Position(open_price=current_price, btc_qty=btc_qty, side=SIDE_BUY, fees_pct=self.fees_pct)
        print('BUY# Price: %f   Qty: %s  TXN Fee: %f' % (self.position.open_price, quote_qty_order, txn_fee))
        print(self.position.__dict__)
        self.orders.append(order)
        print('ORDER: ', order)
        self.init_balance()
        # self._balance = None

    def sell_all_market(self):
        current_price = self.current_price
        balance_btc_in_usdt = (self.balance__spot['BTC'] * current_price)
        txn_fee = self.fees_pct * balance_btc_in_usdt

        quote_qty_order = truncate((balance_btc_in_usdt - txn_fee), 2)

        btc_qty = self.balance__spot['BTC']
        print('quote_qty_order: ', quote_qty_order)

        order = self.rest_client.order_market_sell(symbol=BTCUSDT, quoteOrderQty='%.2f' % quote_qty_order)

        current_price = self.current_price
        self.position = Position(open_price=current_price, btc_qty=btc_qty, side=SIDE_SELL, fees_pct=self.fees_pct)
        print('SELL# Price: %f   Qty: %s  TXN Fee: %f' % (self.position.open_price, quote_qty_order, txn_fee))
        print(self.position.__dict__)
        self.orders.append(order)
        print('ORDER: ', order)
        self.init_balance()
        # self._balance = None

    @property
    def cannot_enter(self):
        '''
                ((((29360 - 29340) / 29340) * 100) - 0.001) >= (-1 * (0.12 / 2))
                wait for price after SELL to drop to half of the percentage of take profit
        '''
        last_trade = self.trades[-1]
        filters = [
            last_trade.side in [SIDE_SELL],
            last_trade.calc_close_pl_pct(self.last_price) >= (-1 * (self.TAKE_PROFIT_PCT / 2)) and last_trade.calc_close_pl_pct(self.last_price) <= (self.TAKE_PROFIT_PCT / 2),
        ]
        return filters

    @property
    def can_enter(self):
        ema_slope = get_ema_slope_degrees(self.dataset.price[-1 * self.EMA_SLOPE_PERIOD:], period=self.EMA_SLOPE_PERIOD)
        filters = [
            ema_slope >= self.EMA_HIGH_THRESHOLD or ema_slope <= self.EMA_LOW_THRESHOLD,
            self.rsi[-1] > self.RSI_HIGH_THRESHOLD or self.rsi[-1] < self.RSI_LOW_THRESHOLD
        ]
        return filters


    @property
    def long_condition_is_valid(self):
        ema_slope = get_ema_slope_degrees(self.dataset.price[-1 * self.EMA_SLOPE_PERIOD:], period=self.EMA_SLOPE_PERIOD)
        market_is_oversold = self.rsi[-1] < self.RSI_LOW_THRESHOLD # Oversold
        market_is_bullish = self.macd_signal[-1] > self.macd[-1]
        filters = [
            all([
                self.ema_short[-1] > self.ema_long[-1],
                self.ema_short[-2] > self.ema_long[-2],
                self.ema_short[-3] > self.ema_long[-3],
            ]),
            all([
                self.ema_short[-1] > self.bbands_middle[-1],
                self.ema_short[-2] > self.bbands_middle[-2],
                self.ema_short[-3] > self.bbands_middle[-3],
            ]),
            market_is_oversold, #and market_is_bullish,
            ema_slope > 0,
            # self.model_rfr.predict([[self.last_price]]) > 0
        ]
        return filters
    '''
            
        # Check if RSI is oversold and MACD signal is bullish
        if rsi[-1] < 30 and macd.macd_signal[-1] > macd.macd[-1]:
            return 'long'
        
        # Check if RSI is overbought and MACD signal is bearish
        elif rsi[-1] > 70 and macd.macd_signal[-1] < macd.macd[-1]:
            return 'short'
    '''
    @property
    def short_condition_is_valid(self):
        ema_slope = get_ema_slope_degrees(self.dataset.price[-1 * self.EMA_SLOPE_PERIOD:], period=self.EMA_SLOPE_PERIOD)
        market_is_overbought = self.rsi[-1] > self.RSI_HIGH_THRESHOLD # Overbought
        market_is_bearish = self.macd_signal[-1] < self.macd[-1]
        filters = [
            all([
                self.ema_short[-1] < self.ema_long[-1],
                self.ema_short[-2] < self.ema_long[-2],
                self.ema_short[-3] < self.ema_long[-3],
            ]),
            all([
                self.ema_short[-1] < self.bbands_middle[-1],
                self.ema_short[-2] < self.bbands_middle[-2],
                self.ema_short[-3] < self.bbands_middle[-3],
            ]),
            market_is_overbought, # and market_is_bearish,
            ema_slope < 0,
            # self.model_rfr.predict([[self.last_price]]) < 0
        ]
        return filters
    

    def analyze_depth(self):

        resistance_prices = [Decimal(pv[0]) for pv in self.depth_resistances]
        support_prices = [Decimal(pv[0]) for pv in self.depth_supports]
        nearest_resistance_price = find_nearest_price(resistance_prices, self.last_price)
        nearest_support_price = find_nearest_price(support_prices, self.last_price)

        print('DEPTH>   SUPPORT: %.2f     RESISTANCE: %.2f' % (nearest_support_price, nearest_resistance_price))

        price_direction = 0
        price_mode = 'SUPPORT'
        if abs(self.last_price - nearest_resistance_price) > abs(self.last_price - nearest_support_price):
            price_direction = nearest_support_price
            price_mode = 'SUPPORT'
        elif abs(self.last_price - nearest_resistance_price) < abs(self.last_price - nearest_support_price):
            price_direction = nearest_resistance_price
            price_mode = 'RESISTANCE'

        return price_mode, price_direction