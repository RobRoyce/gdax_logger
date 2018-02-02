from GDAXLoggerBase import GDAXLoggerBase
from GDAXConstants import GDAXConst
import logging
import time


class GDAXTickerLogger(GDAXLoggerBase):
    """Log GDAX ticker data.

    Attributes:
        cols -- unpacked tuple of string indiciating response field names to
                be logged as the columns of the .csv log file. tuple elements
                should be in `GDAXTickerLogger.LOGGER_FIELDS`.
    """
    LOGGER_FIELDS = [
        GDAXConst.time,
        GDAXConst.product_id,
        GDAXConst.trade_id,
        GDAXConst.price,
        GDAXConst.last_size,
        GDAXConst.side,
        GDAXConst.best_ask,
        GDAXConst.best_bid,
        GDAXConst.open_24h,
        GDAXConst.volume_24h,
        GDAXConst.sequence
    ]
    LOG_FILE_SUFFIX = '-Ticker.csv'
    SLEEP_TIME = 1
    INDEX = 'system_time'

    def __init__(self, *cols):
        if not cols:
            cols = GDAXTickerLogger.LOGGER_FIELDS
        assert(all(field in self.LOGGER_FIELDS for field in cols))
        super().__init__(*cols)

        self._event_log = logging.getLogger(__name__)
        self._event_log.debug("initialized")

    def _get_csv_index(self):
        return time.time()
