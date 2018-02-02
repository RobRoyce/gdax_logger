#!/usr/bin/env python
"""A script that sorts, filters, and concatenates ticker logs.
"""
import logging
import os.path
import pandas as pd

SUFFIX = '-Ticker.csv'
YEAR = '2018'
TIME_DELTA = 25
PRICE_DELTA = 20
PRODUCTS = {
    'BTC': 'BTC-USD',
    'ETH': 'ETH-USD',
    'BCH': 'BCH-USD',
    'LTC': 'LTC-USD'
}


def describe_dataframe(frame):
    """Generates descriptive statistics for each data set.
    """
    log.info('{}:'.format(frame['product_id'].iloc[0]))
    log.info(frame['price'].describe())


def check_price_deltas(frame, price_delta=PRICE_DELTA):
    """Looks for drastic changes in price (slippage) and logs the results.
    """
    prev = frame['price'].iloc[0]
    for index, row in frame.iterrows():
        price = row['price']
        delta = price - prev
        if abs(delta) > price_delta:
            log.warning(
                'PRICE DELTA @ {}'.format(index) +
                ' {} - {} : {:.2f}'.format(prev, price, delta))
        prev = price


def check_time_deltas(frame):
    """Looks for drastic changes in time and logs the results.
    """
    prev = frame.index[0]
    for time in frame.index:
        if time >= (prev + TIME_DELTA):
            log.warning(
                'TIME DELTA {:.5f} - {:.5f} '.format(prev, time) +
                ': {:.5f}'.format(time - prev))
        prev = time


def concatenate_csvs(files):
    """Takes a list of files and concatenates them into a pandas `DataFrame`
    """
    list_ = []
    for file in files:
        tmp = pd.read_csv(file, index_col='system_time',
                          header=0, delimiter=',')
        list_.append(tmp)
    frame = pd.concat(list_)
    return frame


def find_files(arg):
    """Searches the root directory where this file is located
    for csv files containing `arg` and ending in `SUFFIX`
    """
    files = []
    dir_path = os.path.dirname(os.path.realpath(__file__))
    for file in os.listdir(dir_path):
        if arg in file and file.endswith(SUFFIX):
            files.append(file)
    files.sort()
    print(files)
    return files


def get_log():
    """Sets up the logging environment.
    """
    log_fmt = '%(levelname)s %(message)s'
    logging.basicConfig(
        datefmt='%m/%d/%y %H:%M:%S',
        format=log_fmt,
        filename='utility.log',
        level=logging.DEBUG
    )
    log = logging.getLogger(__name__)
    log.debug('started')
    return log


def write_csv(frame):
    """Writes a DataFrame to csv file.
    """
    product_id = frame['product_id'].iloc[0]
    filename = '{}.csv'.format(product_id)
    frame.to_csv(filename)


if __name__ == '__main__':
    log = get_log()
    files = find_files(arg=YEAR)
    frame = concatenate_csvs(files)

    eth_df = frame[frame['product_id'] == 'ETH-USD']
    btc_df = frame[frame['product_id'] == 'BTC-USD']
    bch_df = frame[frame['product_id'] == 'BCH-USD']
    ltc_df = frame[frame['product_id'] == 'LTC-USD']

    for frame in [eth_df, btc_df, bch_df, ltc_df]:
        write_csv(frame)
        describe_dataframe(frame)
        check_time_deltas(frame)
        check_price_deltas(frame)
