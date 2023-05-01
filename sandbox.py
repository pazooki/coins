import asyncio
import sys

from binance import Client, BinanceSocketManager, ThreadedWebsocketManager

from config import CONFIG, TESTNET_CONFIG


class Test:
    def test(self, msg):
        print(msg)



async def main():
    # client = Client(api_key=TESTNET_CONFIG['API_KEY'], api_secret=TESTNET_CONFIG['API_SECRET'], testnet=True)
    # client = Client(api_key=CONFIG['API_KEY'], api_secret=CONFIG['API_SECRET'])
    twm = ThreadedWebsocketManager(api_key=TESTNET_CONFIG['API_KEY'], api_secret=TESTNET_CONFIG['API_SECRET'], testnet=True)

    twm.start()

    t = Test()

    print('calling symbol_ticker_socket... ')
    ts = twm.start_aggtrade_socket(t.test, symbol='BTCUSDT')
    print(ts)

    twm.join()
    # async with ts as ts:
    #     while True:
    #         trade_price_data = await ts.recv()
    #         print(trade_price_data)

if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except (Exception, KeyboardInterrupt) as ex:
        print('Error: ', ex)
        print('Shutting down...')