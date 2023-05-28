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


def diff_pct(first_value, second_value):
    return ((second_value - first_value) / first_value) * 100



import os
import logging.handlers

class Logger:
    def __init__(self):
        log_file = 'data/logs/bidding.log'
        self.log_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=1000000, backupCount=5)
        # log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        log_formatter = logging.Formatter('%(asctime)s %(message)s')
        self.log_handler.setFormatter(log_formatter)

        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(self.log_handler)
        self.logger.setLevel(logging.INFO)

    def log(self, message):
        self.logger.info(message)
        print(message)
        # Check if the log file size exceeds the maximum size and rotate if necessary
        if os.path.getsize(self.log_handler.baseFilename) > 1000000:
            self.log_handler.doRollover()

    def __del__(self):
        # Remove the file handler and close it to ensure that the log file is properly rotated
        self.logger.removeHandler(self.log_handler)
        self.log_handler.close()
