from datetime import datetime
from time import time
from typing import List
import numbers
import threading
import logging
import os


class OrderBook(object):
    """A segment tree based order book containing the volumes
    at every price point between $0.01 and a set price cap.

    Attributes:
        market_price -- A number. The current market price at any
                        given time. Used to differentiate betwen the
                        bid and ask sides of the order book.
        price_cap -- A number. The upper price bound to the order book
                     over which no volumes are saved or considered.
        currency -- A string. The name of the crypto currency that the
                    order book is keeping track of. Used for message
                    and log purposes.

    Methods:
        init_book() -- Build the initial order book and volume segment tree.
        update_volume() -- Update the volume at a given price point.
        set_market_price() -- Set the current market price.
        get_volume_in_range() -- Get the sum of volume within a price range.
        get_total_volume() -- Get the total volume of the entire order book.
        get_market_price() -- Get the current market price.
    """

    # Static Variable
    __event_log = logging.getLogger(__name__)

    def __init__(self, price_cap: float, currency: str):
        if not isinstance(price_cap, numbers.Number):
            raise TypeError('Error: order book price_cap must be a number.\n')

        if price_cap <= 0:
            raise ValueError('Error: order book price_cap must be positive.\n')

        if not isinstance(currency, str):
            raise TypeError('Error: order book currency must be a string.\n')

        currencies = ['BTC-USD', 'BCH-USD', 'ETH-USD', 'LTC-USD']
        if currency not in currencies:
            raise ValueError('Error: {} is not an '.format(currency) +
                             'accepted currency name. The name must be one ' +
                             'of the following: {}'.format(currencies))

        self.__access_lock = threading.Lock()
        self.__market_price = 0
        self.__price_cap = price_cap
        self.__price_points = int(price_cap * 100)
        self.__volume_seg_tree = [0] * (2 * self.__price_points)
        self.__currency = currency

        if self.__currency == 'BTC-USD':
            # Needed to ensure logging environment is setup
            # properly (and only once).
            fmt = '%(asctime)s %(levelname)s ' + \
                '%(name)s.%(funcName)s() %(message)s'
            formatter = logging.Formatter(fmt=fmt)
            handler = logging.FileHandler(
                os.path.join('logs/', 'OrderBook.log'))
            handler.setFormatter(formatter)
            OrderBook.__event_log.setLevel(logging.DEBUG)
            OrderBook.__event_log.addHandler(handler)
            OrderBook.__event_log.debug("initialized " + self.__currency)
        else:
            self.__event_log.debug("initialized " + self.__currency)

    def init_book(self, orders: dict):
        """Builds the initial order book segment tree.

        Arguments:
            orders -- A dictionary. Should contain 2 arrays, one
                      containing the bid orders and one containing
                      the ask orders. Each array contains pairs in
                      the following format: [price, volume]
        """
        with self.__access_lock:
            volumes = self.__gen_vol_array(orders['bids'], orders['asks'])
            self.__build_order_book(volumes)

    def update_volume(self, price: float, volume: float):
        """Update the volume at the input price.n

        Arguments:
            price -- A number. The price point at which the volume
                     is being updated.
            volume -- A number. The new volume at the input price
                      point.
        """
        with self.__access_lock:
            if self.__valid_order(price, volume):
                price_index = self.__price_points + int(float(price) * 100) - 1

                # Update volume at leaf of tree
                self.__volume_seg_tree[price_index] = float(volume)

                # Updates volume sums of parent nodes
                while price_index > 1:
                    self.__volume_seg_tree[price_index >> 1] = (
                        self.__volume_seg_tree[price_index] +
                        self.__volume_seg_tree[price_index ^ 1])
                    price_index >>= 1
            else:
                self.__event_log.warning(
                    '{} volume not set, {} is not a valid price'.format(
                        self.__currency, price))

    def update_market_price(self, price: float):
        """Set the current market price. Market price is used to
        differentiate between the bid and ask sides of the order book.

        Arguments:
            price -- A number. The current market price.
        """
        with self.__access_lock:
            if self.__valid_price(price):
                self.__market_price = float(price)
            else:
                self.__event_log.warning(
                    '{} market price not set {} is not a valid price'.format(
                        self.__currency, price))

    def query(self, percent_ranges: List[float]) -> tuple:
        """Perform a batch query of volumes above and below market price
        that are within input percent ranges of market price.

        Arguments:
            percentage_ranges -- A list of floats. Contains the percentage
                                 ranges that should be queried above and
                                 below market price.

        """
        with self.__access_lock:
            second_time = time()
            server_time = datetime.utcnow().__str__()
            price = self.get_market_price()

            row = [second_time, self.__currency, server_time,
                   price]
            buy_vols = []
            sell_vols = []

            for percent in percent_ranges:
                high = price + ((price * percent) / 100)
                low = price - ((price * percent) / 100)
                buy_vols.append(self.get_volume_in_range(low, price))
                sell_vols.append(self.get_volume_in_range(price, high))

            row.extend(buy_vols)
            row.extend(sell_vols)
            row.append(self.get_total_volume())
            return row

    def built(self) -> bool:
        """Return whether the segment tree is fully constructed
        yet or not. If the total volume (the value of the tree root
        node) is non zero, then the tree has been fully constructed.
        """
        return self.get_total_volume() != 0

    def get_volume_in_range(self,
                            lower_price_bound: float,
                            upper_price_bound: float) -> float:
        """Return the sum of volumes over the input price range.

        Arguments:
            lower_price_bound - A number. The lower bound to the range of
                                prices over which the volumes are to be
                                summed.
            upper_price_bound - A number. The upper bound to the range of
                                prices over which the volumes are to be
                                summed.
        """
        volume_sum = 0
        if(self.__valid_price(lower_price_bound) and
           self.__valid_price(upper_price_bound)):

            # Generate indices from input prices
            left_index = int(float(lower_price_bound) * 100 -
                             1 + self.__price_points)
            right_index = int(float(upper_price_bound + 0.01) * 100 -
                              1 + self.__price_points)

            # Sum all volumes in [lower bound, upper bound)
            while left_index < right_index:
                if left_index & 1:
                    volume_sum += self.__volume_seg_tree[left_index]
                    left_index += 1
                if right_index & 1:
                    right_index -= 1
                    volume_sum += self.__volume_seg_tree[right_index]
                left_index >>= 1
                right_index >>= 1
        else:
            self.__event_log.warning(
                '{} failed to query volume {} to {}'.format(
                    self.__currency, upper_price_bound, lower_price_bound))

        return volume_sum

    def get_total_volume(self) -> float:
        """Return the current total volume of the order book."""
        return self.get_volume_in_range(0.01, self.__price_cap - 0.01)

    def get_market_price(self) -> float:
        """Return the current market price."""
        return self.__market_price

    def __build_order_book(self, volumes: List[float]):
        """Constructs the order book segment tree.

        Argument:
            volumes - A list of floats. An ascending ordered list of volumes
                      constructed from the bid and ask sides of the order book
                      snap shot given by GDAX.

        """
        # Initialize leaves of the segment tree with input volumes
        for i in range(0, self.__price_points):
            self.__volume_seg_tree[self.__price_points + i] = volumes[i]

        # Calculate volume sums of all children for each parent node
        for i in range(self.__price_points - 1, -1, -1):
            self.__volume_seg_tree[i] = (self.__volume_seg_tree[i << 1] +
                                         self.__volume_seg_tree[i << 1 | 1])

    def __gen_vol_array(self,
                        bid_orders: List[List[float]],
                        ask_orders: List[List[float]]) -> List[float]:
        """Generates an array of volumes indexed by price,
        used to build the initial segment tree.

        Arguments:
            buy_orders -- An array of pairs. Each pair contains
                          a price at index 0 and a volume at
                          index 1.
            sell_orders -- An array of pairs. Each pair contains
                           a price at index 0 and a volume at
                           index 1.

        Order book data is given by GDAX in 2 chunks, a bid
        side (buy orders) and an ask side (sell orders).

        Volumes at every price point from $0.01 up to the
        price cap are saved in a consecutive order array.
        """

        # Generate an array to hold every price point
        volumes = [0] * self.__price_points

        # Populate array with all volumes from both sides of
        # the exhange order book that fall under price cap.
        for order in bid_orders:
            if self.__valid_order(order[0], order[1]):
                price_index = int(float(order[0]) * 100) - 1
                volumes[price_index] = float(order[1])

        for order in ask_orders:
            if self.__valid_order(order[0], order[1]):
                price_index = int(float(order[0]) * 100) - 1
                volumes[price_index] = float(order[1])

        return volumes

    def __valid_order(self, price: float, volume: float) -> bool:
        """Return whether the current price and volume consistute
        a valid order. Price and volume must be positive numbers,
        and the input price must be under the current price cap.

        Arguments:
            price -- Type unkown. The order price being checked.
            volume -- Type unkown. The order volume.
        """
        return (self.__valid_price(price) and
                self.__valid_volume(volume))

    def __valid_price(self, price: float) -> bool:
        """Return whether price is a valid number, is positive,
        and is under the current price cap.

        Arguments:
            price -- Type unkown. The price being validated.
        """
        if not self.__valid_number(price, 'price'):
            return False

        price = float(price)
        if price <= 0:
            self.__event_log.warning(
                '{} order book price ${} is not a valid price'.format(
                    self.__currency, price))
            return False

        return self.__price_under_cap(price)

    def __price_under_cap(self, price: float) -> bool:
        """Return whether price is under the current price cap. This method
        does not type check, type checking is assumed to have already occured.

        Arguments:
            price -- Type unkown. The price being validated.
        """
        if price > self.__price_cap:
            # self.__event_log.warning(
            #     '{} order book price is above price cap {}'.format(
            #         self.__currency, self.__price_cap))
            return False
        return True

    def __valid_volume(self, volume: float) -> bool:
        """Return whether volume is a valid number and positive.

        Arguments:
            volume -- Type unkown. The volume being validated.
        """
        if not self.__valid_number(volume, 'volume'):
            return False

        if float(volume) < 0:
            self.__event_log.warning(
                '{} order book volume {} is negative'.format(
                    self.__currency, volume))
            return False

        return True

    def __valid_number(self, number: float, name: str) -> bool:
        """Return whether the input is a valid number.

        Arguments:
            number -- Type unkown. The value being checked.
            name -- A string. The type of value being checked.
        """
        if not isinstance(number, numbers.Number):
            try:
                number = float(number)
            except ValueError:
                self.__event_log.warning(
                    '{} expected a number for \'{}\' but found {}'.format(
                        self.__currency, name, number))
                return False
        return True
