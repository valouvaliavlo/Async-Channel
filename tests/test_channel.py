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
import asyncio
import logging

import pytest

from octobot_channels import Consumer, Producer

from octobot_channels.channels import Channels, Channel
from octobot_channels.util import create_channel_instance

TEST_CHANNEL = "Test"
EMPTY_TEST_CHANNEL = "EmptyTest"
CONSUMER_KEY = "test"


class EmptyTestConsumer(Consumer):
    pass


class EmptyTestProducer(Producer):
    pass


class EmptyTestChannel(Channel):
    CONSUMER_CLASS = EmptyTestConsumer
    PRODUCER_CLASS = EmptyTestProducer


async def empty_test_callback():
    pass


@pytest.mark.asyncio
async def test_get_chan():
    class TestChannel(Channel):
        pass

    Channels.del_chan(TEST_CHANNEL)
    await create_channel_instance(TestChannel, Channels)
    await Channels.get_chan(TEST_CHANNEL).stop()


@pytest.mark.asyncio
async def test_new_consumer_without_producer():
    Channels.del_chan(EMPTY_TEST_CHANNEL)
    await create_channel_instance(EmptyTestChannel, Channels)
    await Channels.get_chan(EMPTY_TEST_CHANNEL).new_consumer(empty_test_callback)
    assert len(Channels.get_chan(EMPTY_TEST_CHANNEL).consumers[EmptyTestConsumer.__name__]) == 1
    await Channels.get_chan(EMPTY_TEST_CHANNEL).stop()


@pytest.mark.asyncio
async def test_send_internal_producer_without_consumer():
    class TestProducer(Producer):
        async def send(self, data, **kwargs):
            await super().send(data)
            await Channels.get_chan(TEST_CHANNEL).stop()

    class TestChannel(Channel):
        PRODUCER_CLASS = TestProducer

    Channels.del_chan(TEST_CHANNEL)
    await create_channel_instance(TestChannel, Channels)
    await Channels.get_chan(TEST_CHANNEL).get_internal_producer().send({})


@pytest.mark.asyncio
async def test_send_producer_without_consumer():
    class TestProducer(Producer):
        async def send(self, data, **kwargs):
            await super().send(data)
            await Channels.get_chan(TEST_CHANNEL).stop()

    class TestConsumer(Consumer):
        async def consume(self):
            while not self.should_stop:
                await self.callback(**(self.queue.get()))

    class TestChannel(Channel):
        PRODUCER_CLASS = TestProducer
        CONSUMER_CLASS = TestConsumer

    Channels.del_chan(TEST_CHANNEL)
    await create_channel_instance(TestChannel, Channels)

    producer = TestProducer(Channels.get_chan(TEST_CHANNEL))
    await producer.send({})


@pytest.mark.asyncio
async def test_send_producer_with_consumer():
    class TestConsumer(Consumer):
        async def consume(self):
            while not self.should_stop:
                await self.callback(**(self.queue.get()))

    class TestChannel(Channel):
        PRODUCER_CLASS = EmptyTestProducer
        CONSUMER_CLASS = TestConsumer

    async def callback(data):
        assert data == "test"
        await Channels.get_chan(TEST_CHANNEL).stop()

    Channels.del_chan(TEST_CHANNEL)
    await create_channel_instance(TestChannel, Channels)
    await Channels.get_chan(TEST_CHANNEL).new_consumer(callback)

    producer = EmptyTestProducer(Channels.get_chan(TEST_CHANNEL))
    await producer.send({"data": "test"})


@pytest.mark.asyncio
async def test_pause_producer_without_consumers():
    class TestProducer(Producer):
        async def pause(self):
            await Channels.get_chan(TEST_CHANNEL).stop()

    class TestChannel(Channel):
        PRODUCER_CLASS = TestProducer
        CONSUMER_CLASS = EmptyTestConsumer

    Channels.del_chan(TEST_CHANNEL)
    await create_channel_instance(TestChannel, Channels)
    await TestProducer(Channels.get_chan(TEST_CHANNEL)).run()


@pytest.mark.asyncio
async def test_pause_producer_with_removed_consumer():
    class TestProducer(Producer):
        async def pause(self):
            await Channels.get_chan(TEST_CHANNEL).stop()

    class TestChannel(Channel):
        PRODUCER_CLASS = TestProducer
        CONSUMER_CLASS = EmptyTestConsumer

    Channels.del_chan(TEST_CHANNEL)
    await create_channel_instance(TestChannel, Channels)
    consumer = await Channels.get_chan(TEST_CHANNEL).new_consumer(empty_test_callback)
    await TestProducer(Channels.get_chan(TEST_CHANNEL)).run()
    await Channels.get_chan(TEST_CHANNEL).remove_consumer(consumer)


@pytest.mark.asyncio
async def test_resume_producer():
    class TestProducer(Producer):
        async def resume(self):
            await Channels.get_chan(TEST_CHANNEL).stop()

    class TestChannel(Channel):
        PRODUCER_CLASS = TestProducer
        CONSUMER_CLASS = EmptyTestConsumer

    Channels.del_chan(TEST_CHANNEL)
    await create_channel_instance(TestChannel, Channels)
    await TestProducer(Channels.get_chan(TEST_CHANNEL)).run()
    await Channels.get_chan(TEST_CHANNEL).new_consumer(empty_test_callback)
