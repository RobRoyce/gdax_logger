import dateutil.parser as dp
from queue import Queue
from time import sleep
import threading
import logging
import json
import time


class GDAXLoggerBase(object):
    """Base class for logging data from the GDAX websocket feed

    Arguments:
        cols -- unpacked tuple of strings indicating response field names to
                be logged as the columns of the .csv log file.

    Mutable Attributes:
        INDEX -- A string used to label the first column of a csv file.

        LOG_FILE_SUFFIX -- A String that will be concatenated
                           to the end of the log filename.

        LOGGER_FIELDS -- A list containing the fields which should be logged.

        SLEEP_TIME -- The amount of time (in seconds) the logger
                      should sleep between buffer flushes.
    """

    # class fields to be specified by the subclass
    LOG_FILE_SUFFIX = None
    LOGGER_FIELDS = None
    SLEEP_TIME = 0.1
    INDEX = None

    def __init__(self, *cols):
        if len(cols) == 0:
            raise ValueError

        self._buffer = Queue()
        self._cols = cols
        self._count = None
        self._event_log = logging.getLogger(__name__)
        self._logfile = None
        self._logger_thread = threading.Thread(target=self.__flusher)
        self._prev_data = None
        self._stop = False

        self._logger_thread.start()
        self._event_log.debug("initialized")

    def log(self, ws, data):
        """write data to the log file

           Logging is done via a buffer, so the changes to the log file might
           not be effective immediately.

           arguments:
                data -- data to be logged.
        """
        if 'time' in data:
            self._buffer.put(data)
        else:
            self._event_log.warning("data retrieved with no 'time' key")

    def close(self):
        """close the logger."""
        self._stop = True
        self._logger_thread.join()
        if self._logfile and not self._logfile.closed:
            self._logfile.close()

    def is_running(self):
        return not self._stop

    def start(self):
        pass

    def stop(self):
        pass

    def _get_csv_index(self):
        return time.time()

    def __create_log_file(self, filename, cols):
        self._logfile = open(filename, 'x')
        self._logfile.close()
        self._logfile = open(filename, 'a')

        row = ''
        for key in cols:
            row += '{},'.format(key)
        row = row[:-1]  # remove extra comma
        self._logfile.write(row)
        self._logfile.write('\n')

        self._event_log.info("created new log file")

    def __flush_buffer(self):
        """
        Retrieves data from buffer, filters it,
        then writes to and saves the file.
        """
        while not self._buffer.empty():
            data_str = self.__get_data()
            fdata = self.__get_filtered_data(data_str)
            try:
                self.__write_log_file(fdata)
            except AssertionError:
                self._event_log.exception("cannot write to csv")
                self.__rollback(data_str)
        if self._logfile:
            self._logfile.flush()

    def __flusher(self):
        while not self._stop:
            self.__flush_buffer()
            sleep(self.SLEEP_TIME)

    def __get_data(self):
        if self._prev_data is None:
            data_str = self._buffer.get()
        else:
            data_str = self._prev_data
            self._prev_data = None
        return data_str

    def __get_filename_from(self, timestamp):
        prefix = self.__get_filename_timestamp(timestamp)
        suffix = self.__class__.LOG_FILE_SUFFIX
        return "{}{}".format(prefix, suffix)

    def __get_filename_timestamp(self, time):
        return str(dp.parse(time).astimezone().date())

    def __get_filtered_data(self, data_str):
        """
        Converts a JSON string into a dict with self._cols as a filter.

        The JSON string may contain various fields that we don't want to save.
        This method will ignore those fields and return a filtered dict.

        To customize a subclass's indexing scheme:
            - Declare an INDEX variable (string)
            - Override the _get_csv_index() method
        """
        if self.INDEX is None:
            self.INDEX = 'INDEX'
        fdata = {self.INDEX: self._get_csv_index()}
        data = json.loads(data_str)
        for key in data:
            if key in self._cols:
                fdata[key] = data[key]
        return fdata

    def __resolve_file(self, fdata):
        filename = self.__get_filename_from(fdata['time'])
        if self._logfile is None or self._logfile.name != filename:
            if self._logfile:
                self._logfile.close()
            try:
                self.__create_log_file(filename, fdata.keys())
            except FileExistsError:
                self._logfile = open(filename, 'a')
        assert self._logfile

    def __rollback(self, data_str):
        self._prev_data = data_str

    def __write_log_file(self, fdata):
        """
        Writes a JSON dict to csv file.
        """
        self.__resolve_file(fdata)

        row = ''
        for key in fdata:
            row += '{},'.format(fdata[key])
        row = row[:-1]  # remove extra comma
        self._logfile.write(row)
        self._logfile.write('\n')

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
