import sys
import time
import pandas as pd

from datetime import datetime
from decimal import Decimal
from binance.enums import *
from models.depth import depth_kmeans

from utils import ts_now

POS_WIN = 'WIN'
POS_LOSS = 'LOSS'
POS_INIT = 'INIT'

class Position:
    def __init__(self, open_price=0, btc_qty=0, side=SIDE_BUY, fees_pct=Decimal('0.10')):
        self.open_ts = ts_now()
        self.close_ts = None
        self.open_price = open_price
        self.close_price = None
        self.btc_qty = btc_qty
        self.side = side
        self.status = None
        self.fees_pct = fees_pct
        self.commission = Decimal('0.00000000')
    
    @property
    def pl(self):
        if self.close_price is None:
            raise Exception('Position.close() must be called before Position.pl')
        # only price diff, no total
        if self.side == SIDE_BUY:
            return ((self.open_price - self.close_price) * self.btc_qty) - self.commission
        elif self.side == SIDE_SELL:
            pl = ((self.open_price - self.close_price) * self.btc_qty) - self.commission
            if pl < 0:
                return abs(pl)
            else:
                return -1 * pl
    
    @property
    def pl_pct(self) -> Decimal:
        if self.close_price is None:
            raise Exception('Position.close() must be called before Position.pl_pct')
        return (((self.close_price - self.open_price) / self.open_price) * Decimal('100')) - self.fees_pct
            
    
    def calc_pl_pct(self, last_price) -> Decimal:
        return (((last_price - self.open_price) / self.open_price) * Decimal('100')) - self.fees_pct
    
    def calc_close_pl_pct(self, last_price) -> Decimal:
        '''
            ((((29360 - 29340) / 29340) * 100) - 0.001)
        '''
        return (((last_price - self.close_price) / self.close_price) * Decimal('100')) - self.fees_pct

    # @property
    # def fees(self) -> Decimal:
    #     if self.status in [POS_INIT]:
    #         # get the fee from the last_order always
    #         return Decimal('0.00')
    #     if self.close_price is None:
    #         raise Exception('Position.close() must be called before Position.fees')
    #     return -1 * (self.btc_qty * self.close_price) * self.fees_pct

    def close(self, price, status, commission) -> None:
        self.close_ts = ts_now()
        self.close_price = price
        self.status = status
        self.commission = commission
    
    def take_profit(self, price, commission) -> None:
        self.close(price, POS_WIN, commission)

    def stop_loss(self, price, commission) -> None:
        self.close(price, POS_LOSS, commission)

    def to_dict(self) -> dict:
        return {
            'open_ts': self.open_ts,
            'close_ts': self.close_ts,
            'open': self.open_price,
            'close': self.close_price,
            'btc_qty': self.btc_qty,
            'side': self.side,
            'status': self.status,
            'commission': self.commission
        }


class Strategy:

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
            take_profit_pct=Decimal('0.2'),
            min_profitable_pct=Decimal('0.12'),
            trades_history=None
        ):
        self.WARM_UP_THRESHOLD = warm_up_threshold
        self.rest_client = rest_client
        self.testing = testing
        self.margin_testing = margin_testing
        # self.dataset_raw_dicts = []
        self.dataset = pd.DataFrame(columns=['ts', 'price', 'qty'], index=['ts',])
        self.dataset = self.dataset.dropna()
        self.depth_dataset = {}
        self.depth_supports, self.depth_resistances = [], []
        
        self.last_price = Decimal('0.0')
        self.highest_high_price = Decimal('0.0')

        self.position = None
        self.trades = []
        self.orders = []
        self.balance__spot = {'BTC': 0, 'USDT': 0}
        self.balance__cross_margin = {'BTC': 0, 'USDT': 0}
        self.fees_pct = fees_pct
        
        self.STOP_LOSS_PCT = stop_loss_pct
        self.TAKE_PROFIT_PCT = take_profit_pct
        self.MIN_PROFITABLE_PCT = min_profitable_pct
        
        self.is_isolated_margin = is_isolated_margin
        self.is_cross_margin = is_cross_margin
        self.leverage = leverage

        self.time__started = datetime.now()
        self.time__current = datetime.now()

        # self.trades_history = trades_history
        if self.is_cross_margin:
            self.init_cross_margin_balance()
        elif self.is_isolated_margin:
            self.init_isolated_margin_balance()
        else:
            self.init_spot_balance()
        print('INIT BALANCE>    ', self.balance)
        print('-' * 160)


    @property
    def current_price(self):
        ticker_price = self.rest_client.get_symbol_ticker(symbol='BTCUSDT')
        return Decimal(ticker_price['price'])
        
    def update_price_dataset(self, record):
        try:
            data = {
                'ts': record['T'],
                'price': Decimal(record['p']),
                'qty': Decimal(record['q'])
            }
            # self.dataset_raw_dicts.append(data)
            # self.dataset = pd.DataFrame.from_dict(self.dataset_raw_dicts)
            # self.dataset.set_index(['ts'], inplace=True)
            self.time__current = datetime.now()
        except Exception as ex:
            print(ex)
            if 'e' in record:
                print('Errors: ', record['m'])
                print('Exiting...')
                sys.exit(-1)
        else:
            self.dataset = pd.concat([self.dataset[-self.WARM_UP_THRESHOLD:], pd.DataFrame(data, columns=['ts', 'price', 'qty'], index=['ts',])])
            self.last_price = Decimal(data['price'])
            

    def update_cross_margin_balance(self, data):
        '''
            update_cross_margin_balance:  {
                'e': 'outboundAccountPosition', 
                'E': 1682546690317, 
                'u': 1682546690316, 
                'B': [{'a': 'BTC', 'f': '0.00081673', 'l': '0.00000000'}, {'a': 'BNB', 'f': '0.00000000', 'l': '0.00000000'}, {'a': 'USDT', 'f': '0.02852780', 'l': '0.00000000'}]
            }
        '''
        if 'e' in data and data['e'] in ['outboundAccountPosition']:
            for wallet in data['B']:
                if wallet['a'] == 'BTC':
                    self.balance__cross_margin['BTC'] = Decimal(wallet['f'])
                elif wallet['a'] == 'USDT':
                    self.balance__cross_margin['USDT'] = Decimal(wallet['f'])
        print('update_cross_margin_balance: ', data)

    def update_spot_balance(self, msg):
        if msg['e'] == 'balanceUpdate':
            if msg['a'] == 'btc':
                self.balance__spot['BTC'] = Decimal(msg['d']['a'])
            elif msg['a'] == 'usdt':
                self.balance__spot['USDT'] = Decimal(msg['d']['a'])
        print('UPDATED BALANCE: ', self.balance__spot)

    def next(self, trade_price_data):
        self.update_price_dataset(trade_price_data)
        if len(self.dataset.index) > self.WARM_UP_THRESHOLD:
            self.update_indicators()
            print('=' * 160)
            self.bid()
        else:
            sys.stdout.write('Warming up with new data... (%d/%d)\r' % (len(self.dataset.index), self.WARM_UP_THRESHOLD))
            sys.stdout.flush()

    def update_depth(self, data):
        # print('update_depth: ', data)
        if self.is_cross_margin:
            self.depth_dataset = {'bids': data['b'], 'asks': data['a']}
        else:
            self.depth_dataset = data
        # print(self.depth_dataset)
        # self.depth_dataset = {'bids': data.get_bids(), 'asks': data.get_asks()}
        # start_time = time.time()
        self.depth_supports, self.depth_resistances = depth_kmeans(self.depth_dataset, n_clusters_limit=5)
        # end_time = time.time()
        # print("Time: ", (end_time - start_time) * 1000, "milliseconds")
        # print('supports: ', self.depth_supports)
        # print('resistances: ', self.depth_resistances)

    
    @property
    def trades_history(self):
        return pd.DataFrame(
            [position.to_dict() for position in self.trades], 
            columns=['open_ts', 'close_ts', 'open', 'close', 'btc_qty', 'side', 'status', 'commission']
        )

    def init_cross_margin_balance(self):
        assets = self.rest_client.get_margin_account()['userAssets']
        self.highest_high_price = self.last_price
        for asset in assets:
            if asset['asset'] == 'BTC':
                self.balance__cross_margin['BTC'] = Decimal(asset['free'])
            elif asset['asset'] == 'USDT':
                self.balance__cross_margin['USDT'] = Decimal(asset['free'])
        return self.balance__cross_margin

    def init_isolated_margin_balance(self):
        assets = self.rest_client.get_isolated_margin_account()['assets'][0]
        self.isolated_margin_balance = {
            'BTC': assets['baseAsset'],
            'USDT': assets['quoteAsset']
        }
        return self.isolated_margin_balance
    
    def init_spot_balance(self):
        btc_balance = self.rest_client.get_asset_balance(asset='BTC')
        usdt_balance = self.rest_client.get_asset_balance(asset='USDT')
        self.balance__spot = {
            'BTC': Decimal(btc_balance['free']),
            'USDT': Decimal(usdt_balance['free']),
        }
        return self.balance__spot
    
    @property
    def balance(self):
        if self.is_cross_margin:
            return self.balance__cross_margin
        else:
            return self.balance__spot
        
    @property
    def current_side(self):
        if self.position is not None:
            return self.position.side
        else:
            if self.balance['USDT'] > self.BALANCE_MIN_USDT:
                return SIDE_BUY
            elif self.balance['BTC'] > self.BALANCE_MIN_BTC:
                return SIDE_SELL


    def update_indicators(self):
        pass

    def bid(self):
        pass