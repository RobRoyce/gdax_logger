#!/usr/bin/env python
""" A script that retrieves and saves ticker data from the GDAX Exchange.

This module establishes a websocket connection with GDAX and
feeds the received messages to the GDAXTickerLogger. Each
message is added to a queue which is emptied regularly on a
separate thread.

All available products on GDAX are being received and saved.
In order to customize which products you receive, you can
remove the products you don't want in the on_open function below.
"""
from GDAXConstants import GDAXConst
from GDAXTickerLogger import GDAXTickerLogger
from websocket import WebSocketApp
from time import time
from websocket._exceptions import *
import websocket
import logging
import json


def ticker_logger():
    with GDAXTickerLogger() as ticker_logger:
        event_log = logging.getLogger(__name__)
        event_log.debug('started')

        def on_open(ws):
            request = json.dumps({
                GDAXConst.request_type: GDAXConst.subscribe,
                GDAXConst.product_ids: [
                    GDAXConst.eth_usd,
                    GDAXConst.btc_usd,
                    GDAXConst.bch_usd,
                    GDAXConst.ltc_usd
                ],
                GDAXConst.channels: [GDAXConst.ticker]
            })
            ws.send(request)

        def on_close(ws):
            event_log.info('websocket closed @ {}'.format(time()))
            event_log.info('stopping...{}'.format('\n' * 5))

        def on_ping(ws, msg):
            event_log.debug('sent')

        def on_pong(ws, msg):
            event_log.debug('received')

        def on_error(ws, error):
            if isinstance(error, (KeyboardInterrupt)):
                event_log.info('interrupt @ {}'.format(time()))
                ticker_logger.close()
            else:
                event_log.exception('{} @ {}'.format(error, time()))

        while ticker_logger.is_running():
            try:
                websocket.enableTrace(True)
                gdax_ws = WebSocketApp(
                    GDAXConst.Live.websocket_url,
                    on_open=on_open,
                    on_close=on_close,
                    on_error=on_error,
                    on_ping=on_ping,
                    on_pong=on_pong
                )
                if gdax_ws is not None:
                    gdax_ws.on_message = ticker_logger.log
                    gdax_ws.run_forever(ping_interval=300)
                else:
                    event_log.warning('unable to init websocket')

            except WebSocketException as error:
                event_log.exception('{} @ {}'.format(error, time()))
            except Exception as error:
                event_log.exception('{} @ {}'.format(error, time()))


if __name__ == '__main__':
    # Setup the logging environment.
    log_fmt = '%(asctime)s %(levelname)s %(name)s.%(funcName)s() %(message)s'
    logging.basicConfig(
        datefmt='%m/%d/%y %H:%M:%S',
        format=log_fmt,
        filename='events.log',
        level=logging.DEBUG
    )
    event_log = logging.getLogger(__name__)
    event_log.debug('started')

    try:
        ticker_logger()
    except Exception as error:
        event_log.exception(error)
