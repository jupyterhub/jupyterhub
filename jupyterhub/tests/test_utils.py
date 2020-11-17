"""Tests for utilities"""
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from async_generator import aclosing
from tornado import gen
from tornado.concurrent import run_on_executor

from ..utils import iterate_until


async def yield_n(n, delay=0.01):
    """Yield n items with a delay between each"""
    for i in range(n):
        if delay:
            await asyncio.sleep(delay)
        yield i


def schedule_future(io_loop, *, delay, result=None):
    """Construct a Future that will resolve after a delay"""
    f = asyncio.Future()
    if delay:
        io_loop.call_later(delay, lambda: f.set_result(result))
    else:
        f.set_result(result)
    return f


@pytest.mark.parametrize(
    "deadline, n, delay, expected",
    [
        (0, 3, 1, []),
        (0, 3, 0, [0, 1, 2]),
        (5, 3, 0.01, [0, 1, 2]),
        (0.5, 10, 0.2, [0, 1]),
    ],
)
async def test_iterate_until(io_loop, deadline, n, delay, expected):
    f = schedule_future(io_loop, delay=deadline)

    yielded = []
    async with aclosing(iterate_until(f, yield_n(n, delay=delay))) as items:
        async for item in items:
            yielded.append(item)
    assert yielded == expected


async def test_iterate_until_ready_after_deadline(io_loop):
    f = schedule_future(io_loop, delay=0)

    async def gen():
        for i in range(5):
            yield i

    yielded = []
    async with aclosing(iterate_until(f, gen())) as items:
        async for item in items:
            yielded.append(item)
    assert yielded == list(range(5))


@gen.coroutine
def tornado_coroutine():
    yield gen.sleep(0.05)
    return "ok"


class TornadoCompat:
    def __init__(self):
        self.executor = ThreadPoolExecutor(1)

    @run_on_executor
    def on_executor(self):
        time.sleep(0.05)
        return "executor"

    @gen.coroutine
    def tornado_coroutine(self):
        yield gen.sleep(0.05)
        return "gen.coroutine"


async def test_tornado_coroutines():
    t = TornadoCompat()
    # verify that tornado gen and executor methods return awaitables
    assert (await t.on_executor()) == "executor"
    assert (await t.tornado_coroutine()) == "gen.coroutine"
