#cython: language_level=2
#  Drakkar-Software OctoBot-Channels
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

from octobot_channels import CONSUMER_CALLBACK_TYPE, CHANNEL_WILDCARD
from octobot_channels.channels.channel_instances import ChannelInstances
from octobot_channels.channels.channel cimport Channel, Channels
from octobot_channels.consumer cimport Consumer


cdef class ExchangeChannel(Channel):
    FILTER_SIZE = 1

    def __init__(self, exchange_manager):
        super().__init__()
        self.exchange_manager = exchange_manager
        self.exchange = exchange_manager.exchange

        self.filter_send_counter = 0
        self.should_send_filter = False

    def new_consumer(self, callback: CONSUMER_CALLBACK_TYPE, **kwargs):
        raise NotImplemented("new consumer is not implemented")

    cdef void will_send(self):
        self.filter_send_counter += 1

    cdef void has_send(self):
        if self.should_send_filter:
            self.filter_send_counter = 0
            self.should_send_filter = False

    cdef object get_consumers(self, str symbol):
        if not symbol:
            symbol = CHANNEL_WILDCARD
        try:
            self.should_send_filter = self.filter_send_counter >= self.FILTER_SIZE
            return [consumer
                    for consumer in self.consumers[symbol]
                    if not consumer.filter_size or self.should_send_filter]
        except KeyError:
            ExchangeChannel._init_consumer_if_necessary(self.consumers, symbol)
            return self.consumers[symbol]

    cdef list get_consumers_by_timeframe(self, object time_frame, str symbol):
        if not symbol:
            symbol = CHANNEL_WILDCARD
        cdef int should_send_filter
        try:
            should_send_filter = self.filter_send_counter >= self.FILTER_SIZE
            if should_send_filter:
                self.filter_send_counter = 0
            return [consumer
                    for consumer in self.consumers[symbol][time_frame]
                    if not consumer.filter_size or should_send_filter]
        except KeyError:
            ExchangeChannel._init_consumer_if_necessary(self.consumers, symbol)
            ExchangeChannel._init_consumer_if_necessary(self.consumers[symbol], time_frame)
            return self.consumers[symbol][time_frame]

    cdef void _add_new_consumer_and_run(self, Consumer consumer, str symbol = CHANNEL_WILDCARD, object time_frame = None):
        if symbol:
            # create dict and list if required
            ExchangeChannel._init_consumer_if_necessary(self.consumers, symbol)

            if time_frame:
                # create dict and list if required
                ExchangeChannel._init_consumer_if_necessary(self.consumers[symbol], time_frame)
                self.consumers[symbol][time_frame].append(consumer)
            else:
                self.consumers[symbol].append(consumer)
        else:
            self.consumers[CHANNEL_WILDCARD] = [consumer]
        consumer.run()
        self.logger.info(f"Consumer started for symbol {symbol}")

    @staticmethod
    cdef void _init_consumer_if_necessary(dict consumer_list, str key):
        if key not in consumer_list:
            consumer_list[key] = []


cdef class ExchangeChannels(Channels):
    @staticmethod
    def set_chan(ExchangeChannel chan, str name) -> None:
        chan_name = chan.get_name() if name else name

        try:
            exchange_chan = ChannelInstances.instance().channels[chan.exchange_manager.exchange.get_name()]
        except KeyError:
            ChannelInstances.instance().channels[chan.exchange_manager.exchange.get_name()] = {}
            exchange_chan = ChannelInstances.instance().channels[chan.exchange_manager.exchange.get_name()]

        if chan_name not in exchange_chan:
            exchange_chan[chan_name] = chan
        else:
            raise ValueError(f"Channel {chan_name} already exists.")

    @staticmethod
    def get_chan(str chan_name, str exchange_name) -> ExchangeChannel:
        return ChannelInstances.instance().channels[exchange_name][chan_name]
