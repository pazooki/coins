import pickle
import sys
import time
import traceback
import ta
import numpy as np
import pandas as pd
import pandas_ta as pta
import talib

from decimal import Decimal
from binance.enums import *

from strategies.strategy import Strategy, Position, POS_LOSS, POS_WIN, POS_INIT
from utils import diff_pct, find_nearest_price, get_ema_slope_degrees, filters_to_signals, truncate


BTCUSDT = 'BTCUSDT'


class Mach1(Strategy):
    SIGNAL_THRESHOLD = 4

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
            margin_testing=False,
            is_isolated_margin=False,
            is_cross_margin=False,
            leverage=1,
            warm_up_threshold=50, 
            fees_pct=Decimal('0.10'), 
            stop_loss_pct=Decimal('0.1'),
            take_profit_pct=Decimal('0.1'),
            # model_rfr,
            trades_history=None,
            logger=None
        ):
        super().__init__(
            rest_client, 
            testing=testing,
            margin_testing=margin_testing,
            is_isolated_margin=is_isolated_margin,
            is_cross_margin=is_cross_margin,
            leverage=leverage, 
            warm_up_threshold=warm_up_threshold, 
            fees_pct=fees_pct, 
            stop_loss_pct=stop_loss_pct, 
            take_profit_pct=take_profit_pct,
            trades_history=trades_history,
            logger=logger
        )
        # self.model_rfr = model_rfr
        self.is_first_order = True
        self.trend_classifier_model = pickle.load(open('/home/mehrdadpazooki/TheVault/trading/code/profit/models/classifier_model.pkl', 'rb'))


    def update_indicators(self):
        self.ema_short = pta.ema(self.dataset.price, length=self.EMA_SHORT_LENGTH, overlay=True)
        self.ema_long = pta.ema(self.dataset.price, length=self.EMA_LONG_LENGTH, overlay=True)
        self.rsi = talib.RSI(self.dataset.price, timeperiod=self.RSI_PERIOD)
        self.bbands_upper, self.bbands_middle, self.bbands_lower = talib.BBANDS(self.dataset.price, timeperiod=self.BB_PERIOD, nbdevup=self.BB_STD_FACTOR, nbdevdn=self.BB_STD_FACTOR)
        self.macd, self.macd_signal, self.macd_hist = talib.MACD(self.dataset.price, fastperiod=self.MACD_FAST, slowperiod=self.MACD_SLOW, signalperiod=self.MACD_SIGNAL)
        self.price_is_uptrend = self.update_price_trend()
        # self.price_is_uptrend = False

    def init_position(self):
        if self.is_first_order:
            self.logger.log('INIT POS>   Is First Order: %s' % self.is_first_order)

            if self.is_isolated_margin:
                # account = self.rest_client.get_isolated_margin_account(symbols="BTCUSDT")
                orders = sorted([i for i in self.rest_client.get_all_margin_orders(symbol="BTCUSDT", isIsolated=True, limit=10) if i['status'] in ['FILLED']], key=lambda x: x['time'], reverse=True)
                last_order = None
                for order in orders:
                    if order['status'] in ['FILLED']:
                        last_order = order
                        break

                executed_qty = Decimal(last_order['executedQty'])
                c_q_qty = Decimal(last_order['cummulativeQuoteQty']) / executed_qty
                # btc_qty = Decimal(account['assets'][0]['baseAsset']['totalAsset'])

                if last_order['side'] == SIDE_BUY:
                    self.position = Position(
                        open_price=c_q_qty, 
                        btc_qty=executed_qty, 
                        side=SIDE_BUY,
                        fees_pct=self.fees_pct
                    )
                elif last_order['side'] == SIDE_SELL:
                    self.position = Position(
                        open_price=c_q_qty, 
                        btc_qty=executed_qty, 
                        side=SIDE_SELL,
                        fees_pct=self.fees_pct
                    )
            elif self.is_cross_margin:
                # account = self.rest_client.get_isolated_margin_account(symbols="BTCUSDT")
                orders = sorted([i for i in self.rest_client.get_all_margin_orders(symbol="BTCUSDT", limit=10) if i['status'] in ['FILLED']], key=lambda x: x['time'], reverse=True)
                
                last_order = None
                for order in orders:
                    if order['status'] in ['FILLED']:
                        last_order = order
                        break

                executed_qty = Decimal(last_order['executedQty'])
                c_q_qty = Decimal(last_order['cummulativeQuoteQty']) / executed_qty
                # btc_qty = Decimal(account['assets'][0]['baseAsset']['totalAsset'])

                if last_order['side'] == SIDE_BUY:
                    self.position = Position(
                        open_price=c_q_qty, 
                        btc_qty=executed_qty, 
                        side=SIDE_BUY,
                        fees_pct=self.fees_pct
                    )
                elif last_order['side'] == SIDE_SELL:
                    self.position = Position(
                        open_price=c_q_qty, 
                        btc_qty=executed_qty, 
                        side=SIDE_SELL,
                        fees_pct=self.fees_pct
                    )
            else:
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
                self.is_first_order = False
            #     self.position.close(current_price, POS_INIT)
            #     self.logger.log('POSITION INIT: ', self.position.__dict__)
            #     self.trades.append(self.position)
            #     self.position = None


    def bid(self):
        self.init_position()
        # price_mode, price_direction = self.analyze_depth()

        long_signals = filters_to_signals(self.long_condition_is_valid)
        short_signals = filters_to_signals(self.short_condition_is_valid)
        # long_signals = all(self.long_condition_is_valid)
        # short_signals = all(self.short_condition_is_valid)

        must_buy = all([
            (not self.trades or self.trades[-1].side == SIDE_SELL),
            self.balance['USDT'] > self.BALANCE_MIN_USDT,
            long_signals > short_signals,
            long_signals >= self.SIGNAL_THRESHOLD,
            # is_uptrend,
            # price_mode in ['SUPPORT']
        ])

        must_sell = all([
            (not self.trades or self.trades[-1].side == SIDE_BUY),
            self.balance['BTC'] > self.BALANCE_MIN_BTC,
            short_signals > long_signals,
            short_signals >= self.SIGNAL_THRESHOLD,
            # not is_uptrend,
            # price_mode in ['RESISTANCE']
        ])

        header = {}
        header.update(self.balance)
        header.update(dict(
            tp=self.TAKE_PROFIT_PCT, 
            sl=self.STOP_LOSS_PCT, 
            st_at=self.time__started.strftime("%d %H:%M:%S"),
            cur_at=self.time__current.strftime("%d %H:%M:%S")
        ))
        self.logger.log('BALANCE:  {BTC:.8f} BTC   {USDT:.2f} USDT    |   TP: {tp}%    SL: {sl}%   |   ST@: {st_at}     CUR@: {cur_at}      |'.format(**header))
        self.logger.log('-' * 140)
        self.logger.log('POS>   PRICE: %.2f   -  CUR PRICE: %.2f   =   DIFF: %.2f    PL_PCT: %.4f%%     |   SIGS>  L: %d %s   S: %d %s    UP_TREND: %s    |' % (
            self.position.open_price,
            self.last_price,
            self.last_price - self.position.open_price,
            self.position.calc_pl_pct(self.last_price),
            long_signals, must_buy, short_signals, must_sell, self.price_is_uptrend
        ))
        self.logger.log('-' * 140)
        self.logger.log('STATS> T#: %d     WINS: %d     LOSSES: %d  |   SIDE: %s    |' % (
            len(self.trades),
            sum(1 if t == POS_WIN else 0 for t in list(self.trades_history.status)),
            sum(1 if t == POS_LOSS else 0 for t in list(self.trades_history.status)),
            self.current_side 
        ))

        # return None

        if not self.can_enter:
            self.logger.log('CANNOT ENTER')
            return None
        
        if must_buy: #self.position.side == SIDE_SELL:# and can_buy and price_mode in ['SUPPORT']:
            if self.has_no_trades:
                self.call_until_executed(self.long_all_market, dict(status=POS_INIT))
            else:
                take_profit_trigger = self.position.calc_pl_pct(self.last_price) < (-self.TAKE_PROFIT_PCT)
                stop_loss_trigger = self.position.calc_pl_pct(self.last_price) >= self.STOP_LOSS_PCT

                if take_profit_trigger:# and price_direction > self.last_price:
                    self.call_until_executed(self.long_all_market, dict(status=POS_WIN))
                elif stop_loss_trigger:# and price_direction > self.last_price:
                    self.call_until_executed(self.long_all_market, dict(status=POS_LOSS))
                else:
                    self.logger.log('ACTION) NO BUY')
        elif must_sell: #and self.position.side == SIDE_BUY:# and price_mode in ['RESISTANCE']:
            if self.has_no_trades:
                self.call_until_executed(self.short_all_market, dict(status=POS_INIT))
            else:
                # self.logger.log('pl_pct: ', self.position.calc_pl_pct(self.last_price))
                take_profit_trigger = self.position.calc_pl_pct(self.last_price) > self.TAKE_PROFIT_PCT
                stop_loss_trigger = self.position.calc_pl_pct(self.last_price) <= self.STOP_LOSS_PCT

                if take_profit_trigger: # and price_direction <= self.last_price and price_mode in ['RESISTANCE']:
                    self.call_until_executed(self.short_all_market, dict(status=POS_WIN))
                elif stop_loss_trigger:# and price_direction < self.last_price:
                    self.call_until_executed(self.short_all_market, dict(status=POS_LOSS))
                else:
                    self.logger.log('ACTION) NO SELL')
        
    
    def long_all_market(self, side_effect=NO_SIDE_EFFECT_TYPE, status=POS_INIT):
        self.logger.log(status)
        # get_max_margin_order_quantity
        current_price = self.current_price
        txn_fee = ((self.balance['USDT'] / current_price) * self.fees_pct)
        btc_qty = (self.balance['USDT'] / current_price)
        quantity = truncate(btc_qty, n=5)
        try:
            order = self.rest_client.create_margin_order(
                symbol=BTCUSDT, 
                side=SIDE_BUY, 
                type=ORDER_TYPE_MARKET, 
                isIsolated=self.is_isolated_margin,
                sideEffectType=side_effect,
                quantity=quantity
            )
            self.orders.append(order)
            self.logger.log('ORDER: ', order)
            commission = sum([Decimal(f['commission']) for f in order['fills']])
            avg_price = sum([Decimal(f['price']) for f in order['fills']]) / len(order['fills'])

            if status == POS_WIN:
                self.logger.log('CLOSING>  @  TAKE-PROFIT     SIDE: %s' % (order['side']))
                self.position.take_profit(price=avg_price, commission=commission)
                self.trades.append(self.position)
            elif status == POS_LOSS:
                self.logger.log('CLOSING>  @  STOP-LOSS     SIDE: %s' % (order['side']))
                self.position.stop_loss(price=avg_price, commission=commission)
                self.trades.append(self.position)

            self.position = Position(open_price=current_price, btc_qty=btc_qty, side=SIDE_BUY, fees_pct=self.fees_pct)
            self.logger.log('LONG# Price: %f   Qty: %f  TXN Fee: %f' % (self.position.open_price, btc_qty, txn_fee))
            self.logger.log(self.position.__dict__)
            if self.is_cross_margin:
                self.init_cross_margin_balance()
            elif self.is_isolated_margin:
                self.init_isolated_margin_balance()
        except Exception as e:
            self.logger.log(e)
            self.logger.log(traceback.format_exc())
            # import pdb;pdb.set_trace()
    
    def short_all_market(self, side_effect=NO_SIDE_EFFECT_TYPE, status=POS_INIT):
        self.logger.log(status)
        current_price = self.current_price
        txn_fee = self.fees_pct * self.balance['BTC']
        btc_qty = self.balance['BTC']
        quantity = truncate(btc_qty, n=5)

        try:
            order = self.rest_client.create_margin_order(
                symbol=BTCUSDT, 
                side=SIDE_SELL, 
                type=ORDER_TYPE_MARKET, 
                isIsolated=self.is_isolated_margin, 
                sideEffectType=side_effect,
                quantity=quantity
            )
            self.orders.append(order)
            self.logger.log('ORDER: ', order)
            commission = sum([Decimal(f['commission']) for f in order['fills']])
            avg_price = sum([Decimal(f['price']) for f in order['fills']]) / len(order['fills'])
            if status == POS_WIN:
                self.logger.log('CLOSING>  @  TAKE-PROFIT     SIDE: %s' % (order['side']))
                self.position.take_profit(price=avg_price, commission=commission)
                self.trades.append(self.position)
            elif status == POS_LOSS:
                self.logger.log('CLOSING>  @  STOP-LOSS     SIDE: %s' % (order['side']))
                self.position.stop_loss(price=avg_price, commission=commission)
                self.trades.append(self.position)
            
            self.position = Position(open_price=current_price, btc_qty=btc_qty, side=SIDE_SELL, fees_pct=self.fees_pct)
            self.logger.log('SHORT# Price: %f   Qty: %f  TXN Fee: %f' % (self.position.open_price, btc_qty, txn_fee))
            self.logger.log(self.position.__dict__)
            if self.is_cross_margin:
                self.init_cross_margin_balance()
            elif self.is_isolated_margin:
                self.init_isolated_margin_balance()
        except Exception as e:
            self.logger.log(e)
            self.logger.log(traceback.format_exc())

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
            self.price_is_uptrend
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
            not self.price_is_uptrend
            # self.model_rfr.predict([[self.last_price]]) < 0
        ]
        return filters
    
    @property
    def trailing_stop_loss_trigger(self):
        try:
            price_difference_pct = diff_pct(self.highest_high_price, self.last_price)
            self.logger.log('TSL>     Highest High: %.2f      Diff HH PCT:    %.2f <= %.2f' % (
                self.highest_high_price, price_difference_pct, self.STOP_LOSS_PCT
            ))
            self.highest_high_price = max(self.highest_high_price, self.last_price)
            if price_difference_pct <= self.STOP_LOSS_PCT:
                return True
            else:
                return False
        except Exception as ex:
            self.logger.log(ex)
            return False
    

    def analyze_depth(self):
        if len(self.depth_resistances) == 0 or len(self.depth_supports) == 0:
            return 'ERR', Decimal('0.0')
        resistance_prices = [Decimal(pv[0]) for pv in self.depth_resistances]
        support_prices = [Decimal(pv[0]) for pv in self.depth_supports]
        nearest_resistance_price = find_nearest_price(resistance_prices, self.last_price)
        nearest_support_price = find_nearest_price(support_prices, self.last_price)

        # self.logger.log('DEPTH>   SUPPORT: %.2f     RESISTANCE: %.2f' % (nearest_support_price, nearest_resistance_price))

        price_direction = Decimal('0.0')
        price_mode = 'SUPPORT'
        if abs(self.last_price - nearest_resistance_price) > abs(self.last_price - nearest_support_price):
            price_direction = nearest_support_price
            price_mode = 'SUPPORT'
        elif abs(self.last_price - nearest_resistance_price) < abs(self.last_price - nearest_support_price):
            price_direction = nearest_resistance_price
            price_mode = 'RESISTANCE'

        return price_mode, price_direction


    def update_price_trend(self):
        try:
            df_rec = pd.DataFrame.from_dict(self.kline)
            trend_prediction = self.trend_classifier_model.predict(df_rec)
            return True if trend_prediction[0] in [1] else False
        except Exception as ex:
            self.logger.log(self.kline)
            self.logger.log(ex)
            return False