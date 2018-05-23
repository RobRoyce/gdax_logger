#!/usr/bin/env python
""" A script that retrieves ticker and orderbook data from the GDAX Exchange.
"""
from gdax_logger.LoggerHandler import LoggerHandler
from websocket._exceptions import *
from websocket import WebSocketApp
from gdax_logger import GDAXConst
from time import time
import websocket
import logging
import errno
import json
import os


def on_open(ws):
    """ Sends the initial request to GDAX."""
    request = json.dumps({
        GDAXConst.request_type: GDAXConst.subscribe,
        GDAXConst.product_ids: [
            GDAXConst.btc_usd,
            GDAXConst.eth_usd,
            GDAXConst.ltc_usd,
            GDAXConst.bch_usd
        ],
        GDAXConst.channels: [
            GDAXConst.ticker,
            GDAXConst.matches,
            GDAXConst.level2
        ]
    })
    ws.send(request)
    event_log.debug('request sent:\n{0}'.format(request))


def on_close(ws, *args):
    event_log.info('websocket closed @ {}'.format(time()))
    event_log.info('stopping...{}'.format('\n' * 5))


def on_message(ws, data):
    if GDAXConst.ticker in data:
        if 'time' in data:
            handler.insert_ticker(data)
        else:
            event_log.warning('received update with no timestamp')
    else:
        handler.update_order_book(data)


def on_error(ws, error):
    if isinstance(error, (KeyboardInterrupt)):
        event_log.warning('interrupt @ {}'.format(time()))
        handler.close()
    else:
        event_log.exception('{} @ {}'.format(error, time()))


if __name__ == '__main__':
    if not os.path.exists('logs'):
        try:
            os.makedirs('logs')
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    fmt = '%(asctime)s %(levelname)s %(name)s.%(funcName)s() %(message)s'
    formatter = logging.Formatter(fmt=fmt)
    handler = logging.FileHandler(os.path.join('logs/', 'main.log'))
    handler.setFormatter(formatter)
    event_log = logging.getLogger(__name__)
    event_log.setLevel(logging.DEBUG)
    event_log.addHandler(handler)
    event_log.debug('started')

    with LoggerHandler() as handler:
        while handler.is_running():
            try:
                websocket.enableTrace(False)
                gdax_ws = WebSocketApp(
                    GDAXConst.Live.websocket_url,
                    on_open=on_open,
                    on_close=on_close,
                    on_error=on_error
                )
                if gdax_ws is not None:
                    gdax_ws.on_message = on_message
                    gdax_ws.run_forever(ping_interval=15)
                else:
                    event_log.warning('unable to init websocket')

            except WebSocketException as error:
                event_log.exception('{} @ {}'.format(error, time()))
            except Exception as error:
                event_log.exception('{} @ {}'.format(error, time()))
