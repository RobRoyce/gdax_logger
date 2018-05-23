from .GDAXConstants import GDAXConst
from .OrderBook import OrderBook
from datetime import datetime
from sqlite3 import Error
from time import sleep
from time import time
import threading
import requests
import sqlite3
import logging
import json
import os


class LoggerHandler(object):
    _event_log = logging.getLogger(__name__)

    def __init__(self):
        # Initialize Logging environment
        fmt = '%(asctime)s %(levelname)s %(name)s.%(funcName)s() %(message)s'
        formatter = logging.Formatter(fmt=fmt)
        handler = logging.FileHandler(os.path.join('logs/', 'Handler.log'))
        handler.setFormatter(formatter)
        _event_log = logging.getLogger(__name__)
        _event_log.setLevel(logging.DEBUG)
        _event_log.addHandler(handler)

        # Initialize class variables
        self.__closed = False
        self.__post_to_slack = False
        self.__slack_url = ''
        self.__last_error = (time() - 300)
        self.__DB_TIMEOUT = 0.15
        self.__OB_PATH = 'order_books.db'
        self.__TICKER_PATH = 'tickers.db'
        self.__logger_thread = threading.Thread(
            target=self.__query_thread, daemon=True)

        # Initialize Databasse
        sqlite3.enable_callback_tracebacks(True)
        self.__init_database()

        # Initialize order books and loggers
        self.percent_ranges = [0.01, 0.05, 0.1, 0.5, 1, 2.5, 5, 10, 25]
        self.product_ids = [
            GDAXConst.btc_usd,
            GDAXConst.eth_usd,
            GDAXConst.ltc_usd,
            GDAXConst.bch_usd
        ]
        self._order_books = {
            GDAXConst.btc_usd: OrderBook(50000, GDAXConst.btc_usd),
            GDAXConst.eth_usd: OrderBook(10000, GDAXConst.eth_usd),
            GDAXConst.ltc_usd: OrderBook(5000, GDAXConst.ltc_usd),
            GDAXConst.bch_usd: OrderBook(20000, GDAXConst.bch_usd)
        }
        self.ticker_columns = [
            GDAXConst.system_time, GDAXConst.server_time, GDAXConst.product_id,
            GDAXConst.price, GDAXConst.open_24h, GDAXConst.volume_24h,
            GDAXConst.best_bid, GDAXConst.best_ask, GDAXConst.side,
            GDAXConst.last_size
        ]
        self.__logger_thread.start()
        self._event_log.debug("initialized...")

    def close(self):
        self._event_log.info('stopping...')
        self.__closed = True
        self.__logger_thread.join()

    def is_running(self):
        return not self.__closed

    def insert_ticker(self, json_str):
        fdata = {
            'system_time': time(),
            'server_time': datetime.utcnow().__str__()
        }

        # Filter out unwanted data points
        data = json.loads(json_str)
        for key in data:
            if key in self.ticker_columns:
                fdata[key] = data[key]

        # Convert the dict to a list
        row = []
        for key in fdata:
            row.append(fdata[key])

        sql = 'INSERT INTO tickers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        path = self.__TICKER_PATH

        self.__write_to_db(path, sql, row)

    def update_order_book(self, data):
        data = json.loads(data)
        if GDAXConst.l2update in data['type']:
            product = data['product_id']
            price = data['changes'][0][1]
            volume = data['changes'][0][2]
            if product in self.product_ids:
                self._order_books[product].update_volume(price, volume)

        if GDAXConst.match in data['type']:
            product = data['product_id']
            if product in self.product_ids:
                self._order_books[product].update_market_price(data['price'])

        if GDAXConst.snapshot in data['type']:
            product = data['product_id']
            if product in self.product_ids:
                self._order_books[product].init_book(data)

    def __create_connection(self, db_file, timeout=None):
        if timeout is None:
            timeout = self.__DB_TIMEOUT
        try:
            connection = sqlite3.connect(db_file, timeout=timeout)
            return connection
        except Error as e:
            self._event_log.critical(
                'unable to connect to {} due to \"{}\"'.format(db_file, e))
        return None

    def __init_database(self):
        self._event_log.info('Attempting to initialize database...')

        path = self.__TICKER_PATH
        sql = """CREATE TABLE IF NOT EXISTS tickers
            (system_time real PRIMARY KEY, server_time text, product_id text,
            price real, open_24h real, volume_24h real, best_bid real,
            best_ask real, side text, last_size real);"""
        status = self.__write_to_db(path, sql)
        if status is None:
            self._event_log.critical(
                'Failed to create `tickers` table in {}'.format(path))
            raise Exception

        sql = """CREATE TABLE IF NOT EXISTS order_books (
            system_time real PRIMARY KEY, product_id text,
            server_time text, price real, buy_vol_0001 real,
            buy_vol_0005 real, buy_vol_0010 real, buy_vol_0050 real,
            buy_vol_0100 real, buy_vol_0250 real, buy_vol_0500 real,
            buy_vol_1000 real, buy_vol_2500 real, sell_vol_0001 real,
            sell_vol_0005 real, sell_vol_0010 real, sell_vol_0050 real,
            sell_vol_0100 real, sell_vol_0250 real, sell_vol_0500 real,
            sell_vol_1000 real, sell_vol_2500 real, total real); """
        path = self.__OB_PATH
        status = self.__write_to_db(path, sql)
        if status is None:
            self._event_log.critical(
                'Failed to create `order_books` table in {}'.format(path))
            raise Exception

    def __query_thread(self):
        while not self.__closed:
            self.__query_order_books()
            sleep(0.9835)
            '''
            This was a trial/error value that seems to generate consistent output.
            i.e. sequential order book queries tend to stay within 0.1 second
            of each other. This value might not be optimal for your system.
            '''

    def __query_order_books(self):
        for product_id in self.product_ids:
            order_book = self._order_books[product_id]
            if not order_book.built():
                continue

            row = tuple(order_book.query(self.percent_ranges))
            sql = '''
                INSERT INTO order_books VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )'''
            self.__write_to_db(self.__OB_PATH, sql, row)

    def __write_to_db(self, path, sql, row=None, timeout=None):
        try:
            conn = self.__create_connection(path, timeout)
            conn.execute(sql) if (row is None) else conn.execute(sql, row)
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            self._event_log.critical('''{} @ {}
            <SQL>{}
            </SQL>
            <Data>
            \t{}
            </Data>
            '''.format(e, time(), sql, row))

            err = e.__str__()
            if "database is locked" not in err and "UNIQUE" not in err:
                if self.__last_error <= time() - 300:
                    self.__last_error = time()
                    msg = {"text": "Something went wrong: {}".format(e)}
                    self.__write_to_slack(msg)
            ''' Note: These are strictly preference, you can pick
                and choose which errors you don't want to receive.'''
            return None

    def __write_to_slack(self, msg):
        if self.__post_to_slack:
            requests.post(self.__slack_url, json=msg)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()
