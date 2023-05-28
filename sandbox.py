import asyncio
import sys

from binance import Client, BinanceSocketManager, ThreadedWebsocketManager

from config import CONFIG, TESTNET_CONFIG


class Test:
    def test(self, msg):
        print(msg)



def main():
    # client = Client(api_key=TESTNET_CONFIG['API_KEY'], api_secret=TESTNET_CONFIG['API_SECRET'], testnet=True)
    # client = Client(api_key=CONFIG['API_KEY'], api_secret=CONFIG['API_SECRET'])

    # print([i for i in client.get_margin_account()['userAssets'] if i['asset'] in ['BTC', 'USDT']])
    # orders = client.get_all_margin_orders(symbol='BTCUSDT', limit=4)
    # for o in orders:
    #     print(o)
    twm = ThreadedWebsocketManager(api_key=CONFIG['API_KEY'], api_secret=CONFIG['API_SECRET'], testnet=False)
    twm.start()
    t = Test()
    print('calling symbol_ticker_socket... ')
    ts = twm.start_aggtrade_socket(print, symbol='BTCUSDT')
    print(ts)
    twm.join()
    # async with ts as ts:
    #     while True:
    #         trade_price_data = await ts.recv()
    #         print(trade_price_data)

if __name__ == '__main__':
    try:
        # loop = asyncio.get_event_loop()
        # loop.run_until_complete(main())
        main()
    except (Exception, KeyboardInterrupt) as ex:
        print('Error: ', ex)
        print('Shutting down...')


