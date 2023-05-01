import sys
import time

PROJECT_PATH = '/home/mehrdadpazooki/TheVault/trading/code/darksteps'

# caution: path[0] is reserved for script path (or '' in REPL)
sys.path.insert(1, PROJECT_PATH)

from binance.client import Client
from sklearn.tree import DecisionTreeClassifier

import pandas as pd
import numpy as np
import pickle

from binance.enums import *

from config import CONFIG

# Set up the Binance API client
client = Client(CONFIG['API_KEY'], CONFIG['API_SECRET'])
symbol = 'BTCUSDT'

def build_dtc():
    print('build_dtc initialized...')
    # Set up the parameters for the API request
    interval = Client.KLINE_INTERVAL_15MINUTE
    start_time = '5 year ago UTC'

    # Make the API request
    klines = client.get_historical_klines(symbol, interval, start_time)
    data = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignored'])

    # Convert the timestamp to a datetime object
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')

    # Prepare the data
    X = data['close'].values.reshape(-1, 1)
    y = [1 if data['close'][i+1] > data['close'][i] else 0 for i in range(len(data)-1)]
    X = X[:-1]

    print('Training the model...')
    # Train the model
    model = DecisionTreeClassifier().fit(X, y)
    # Store the model in a file
    with open(PROJECT_PATH + '/models/dtc_model.pkl', 'wb') as f:
        pickle.dump(model, f)
    return model


def get_dtc():
    try:
        with open(PROJECT_PATH + '/models/dtc_model.pkl', 'rb') as f:
            print('Loading from stored dtc_model.pkl')
            model = pickle.load(f)
            if hasattr(model, 'predict'):
                return model
    except Exception as ex:
        print(ex)
        print('dtc_model.pkl was not available.')
        print('Building the model from the scratch...')
        return build_dtc()

if __name__ == '__main__':
    dtc_model = get_dtc()
    while True:
        # Get the current price of Bitcoin
        price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        # Make a prediction
        prediction = dtc_model.predict([[price]])

        print(('Price: ', price, ' Up' if prediction == 1 else 'Down'))
        time.sleep(1)