from decimal import Decimal
from binance import Client, ThreadedWebsocketManager, ThreadedDepthCacheManager
from binance.enums import *
from optparse import OptionParser

import pandas as pd

from config import CONFIG, TESTNET_CONFIG
from utils import ts_filename
from strategies.dark_steps import DarkSteps


BTCUSDT = 'BTCUSDT'

def main(strategy, is_testing):
    config = TESTNET_CONFIG if is_testing else CONFIG

    twm = ThreadedWebsocketManager(api_key=config['API_KEY'], api_secret=config['API_SECRET'], testnet=is_testing)
    # dcm = ThreadedDepthCacheManager(api_key=config['API_KEY'], api_secret=config['API_SECRET'], testnet=is_testing)
    # dcm.start()
    twm.start()
    if strategy.is_cross_margin:
        # twm.start_depth_socket(callback=strategy.update_depth, symbol=BTCUSDT)
        twm.start_aggtrade_socket(callback=strategy.next, symbol=BTCUSDT)
        twm.start_margin_socket(callback=strategy.update_cross_margin_balance)
    else:
        # twm.start_depth_socket(callback=strategy.update_depth, symbol=BTCUSDT, depth=10, interval=100)
        # twm.start_depth_socket(callback=strategy.update_depth, symbol=BTCUSDT, depth=10)
        twm.start_aggtrade_socket(callback=strategy.next, symbol=BTCUSDT)
        twm.start_user_socket(callback=strategy.update_spot_balance)
    # dcm.join()
    twm.join()
    

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-t", "--test", action="store_true", dest="test", default=False, help="Running on testnet for only Spot")
    parser.add_option("-c", "--cross-margin", action="store_true", dest="is_cross_margin", default=False, help="Enable Cross Margin")
    parser.add_option("-i", "--isolated-margin", action="store_true", dest="is_isolated_margin", default=False, help="Enable 10x isolated margin")
    parser.add_option("-l", "--leverage", dest="leverage", default=1, help="Leverage multiplier")
    parser.add_option("-p", "--profit-pct", dest="profit_pct", default=Decimal('0.34'), help="Leverage multiplier")
    (options, args) = parser.parse_args()

    print('Mode: ', 'Test' if options.test else 'Live')

    IS_TESTING = options.test
    if IS_TESTING:
        client = Client(api_key=TESTNET_CONFIG['API_KEY'], api_secret=TESTNET_CONFIG['API_SECRET'], testnet=IS_TESTING)
        # async_client = AsyncClient.create(api_key=TESTNET_CONFIG['API_KEY'], api_secret=TESTNET_CONFIG['API_SECRET'], testnet=IS_TESTING)
    else:
        client = Client(api_key=CONFIG['API_KEY'], api_secret=CONFIG['API_SECRET'])
        # async_client = AsyncClient.create(api_key=CONFIG['API_KEY'], api_secret=CONFIG['API_SECRET'])

    profit_pct = Decimal(options.profit_pct)

    strategy = DarkSteps(
        rest_client=client,
        testing=IS_TESTING,
        is_isolated_margin=options.is_isolated_margin,
        is_cross_margin=options.is_cross_margin,
        leverage=int(options.leverage),
        warm_up_threshold=50,
        fees_pct=Decimal('0.001'),
        
        # -0.2 and 0.7 best backtesting results
        stop_loss_pct=-1 * profit_pct,
        take_profit_pct=profit_pct,
        # model_rfr=model_rfr,
        trades_history=[]
    )
    try:
        main(strategy, is_testing=IS_TESTING)
    except (Exception, KeyboardInterrupt) as ex:
        print(ex)
        trades_history_path = 'data/trades_{ts}{is_testing}.csv'.format(ts=ts_filename(), is_testing='_test' if IS_TESTING else '')
        strategy.trades_history.to_csv(trades_history_path, sep=',', encoding='utf-8')
        print(strategy.trades_history)
        print(trades_history_path)
        # print(strategy.orders)