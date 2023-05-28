from decimal import Decimal
from binance import Client, ThreadedWebsocketManager, ThreadedDepthCacheManager
from binance.enums import *
from optparse import OptionParser

import pandas as pd
import traceback

from config import CONFIG, TESTNET_CONFIG
from utils import ts_filename
from strategies.mach1 import Mach1

from utils import Logger

logger = Logger()

BTCUSDT = 'BTCUSDT'

def main(strategy, is_testing):
    config = TESTNET_CONFIG if is_testing else CONFIG

    twm = ThreadedWebsocketManager(api_key=config['API_KEY'], api_secret=config['API_SECRET'], testnet=is_testing)
    # dcm = ThreadedDepthCacheManager(api_key=config['API_KEY'], api_secret=config['API_SECRET'], testnet=is_testing)
    # dcm.start()
    twm.start()
    if strategy.is_isolated_margin:
        # twm.start_depth_socket(callback=strategy.update_depth, symbol=BTCUSDT)
        twm.start_kline_socket(callback=strategy.update_kline, symbol=BTCUSDT)
        twm.start_aggtrade_socket(callback=strategy.next, symbol=BTCUSDT)
        twm.start_margin_socket(callback=strategy.update_cross_margin_balance)
    elif strategy.is_cross_margin:
        # twm.start_depth_socket(callback=strategy.update_depth, symbol=BTCUSDT)
        twm.start_kline_socket(callback=strategy.update_kline, symbol=BTCUSDT)
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
    parser.add_option("-t", "--test", action="store_true", dest="testing", default=False, help="Running on testnet for only Spot")
    parser.add_option("--cross-margin", action="store_true", dest="is_cross_margin", default=False, help="Enable Cross Margin")
    parser.add_option("--isolated-margin", action="store_true", dest="is_isolated_margin", default=False, help="Enable 10x isolated margin")

    parser.add_option("--margin-test", action="store_true", dest="margin_testing", default=False, help="Running on testnet for only Spot")
    parser.add_option("--trade", action="store_true", dest="trade", default=False, help="Must be used along with margin sell or buy")
    parser.add_option("--margin-sell-all", action="store_true", dest="margin_sell_all", default=False, help="Enable 10x isolated margin")
    parser.add_option("--margin-buy-all", action="store_true", dest="margin_buy_all", default=False, help="Enable 10x isolated margin")

    parser.add_option("--leverage", dest="leverage", default=1, help="Leverage multiplier")
    parser.add_option("--tp-pct", dest="tp_pct", default=Decimal('0.34'), help="Take Profit %")
    parser.add_option("--sl-pct", dest="sl_pct", default=Decimal('0.34'), help="Stop Loss %")
    (options, args) = parser.parse_args()

    print('Mode: ', 'Test' if options.testing else 'Live')

    IS_TESTING = options.testing
    if IS_TESTING and not options.is_cross_margin:
        client = Client(api_key=TESTNET_CONFIG['API_KEY'], api_secret=TESTNET_CONFIG['API_SECRET'], testnet=IS_TESTING)
        # async_client = AsyncClient.create(api_key=TESTNET_CONFIG['API_KEY'], api_secret=TESTNET_CONFIG['API_SECRET'], testnet=IS_TESTING)
    else:
        client = Client(api_key=CONFIG['API_KEY'], api_secret=CONFIG['API_SECRET'])
        # async_client = AsyncClient.create(api_key=CONFIG['API_KEY'], api_secret=CONFIG['API_SECRET'])

    tp_pct = Decimal(options.tp_pct)
    sl_pct = Decimal(options.sl_pct)

    strategy = Mach1(
        rest_client=client,
        testing=IS_TESTING,
        margin_testing=options.margin_testing,
        is_isolated_margin=options.is_isolated_margin,
        is_cross_margin=options.is_cross_margin,
        leverage=int(options.leverage),
        warm_up_threshold=50,
        fees_pct=Decimal('0.001'),
        
        # -0.2 and 0.7 best backtesting results
        stop_loss_pct=-1 * sl_pct,
        take_profit_pct=tp_pct,
        # model_rfr=model_rfr,
        trades_history=[],
        logger=logger
    )
    try:
        if options.trade:
            if options.margin_buy_all:
                strategy.long_all_market()
            elif options.margin_sell_all:
                strategy.short_all_market()
        else:
            main(strategy, is_testing=IS_TESTING)
    except (Exception, KeyboardInterrupt) as ex:
        # traceback.print_exc()
        logger.log(ex)
        trades_history_path = 'data/trades_{ts}{is_testing}.csv'.format(ts=ts_filename(), is_testing='_test' if IS_TESTING or options.margin_testing else '')
        strategy.trades_history.to_csv(trades_history_path, sep=',', encoding='utf-8')
        logger.log(strategy.trades_history)
        logger.log(trades_history_path)
        # print(strategy.orders)