from scipy.stats import linregress
from datetime import datetime

import math
import time

def get_ema_slope_degrees(close, period=3):
    x = sorted([x for x in range(period - 1, -1, -1)])
    y = [float(i) for i in (close[(-1 * period):]).to_list()]
    slope = linregress(x, y)
    return slope.slope

def filters_to_signals(filters):
    # signals = 0
    # for f in filters:
    #     signals += 1 if f else 0
    # return signals
    return sum(filters)

def truncate(f, n=2):
    return math.floor(f * 10 ** n) / 10 ** n


def ts_now():
    return int(time.time() * 1000)


def ts_filename():
    now = datetime.now()
    filename = now.strftime("%Y_%m_%d_%H_%M_%S")
    return filename


def find_nearest_price(prices, target_price):
    return min(prices, key=lambda x: abs(x - target_price))