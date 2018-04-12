"""Tests for utilities"""

import asyncio
import pytest

from async_generator import aclosing, async_generator, yield_
from ..utils import iterate_until


@async_generator
async def yield_n(n, delay=0.01):
    """Yield n items with a delay between each"""
    for i in range(n):
        if delay:
            await asyncio.sleep(delay)
        await yield_(i)


def schedule_future(io_loop, *, delay, result=None):
    """Construct a Future that will resolve after a delay"""
    f = asyncio.Future()
    if delay:
        io_loop.call_later(delay, lambda: f.set_result(result))
    else:
        f.set_result(result)
    return f


@pytest.mark.gen_test
@pytest.mark.parametrize("deadline, n, delay, expected", [
    (0, 3, 1, []),
    (0, 3, 0, [0, 1, 2]),
    (5, 3, 0.01, [0, 1, 2]),
    (0.5, 10, 0.2, [0, 1]),
])
async def test_iterate_until(io_loop, deadline, n, delay, expected):
    f = schedule_future(io_loop, delay=deadline)

    yielded = []
    async with aclosing(iterate_until(f, yield_n(n, delay=delay))) as items:
        async for item in items:
            yielded.append(item)
    assert yielded == expected


@pytest.mark.gen_test
async def test_iterate_until_ready_after_deadline(io_loop):
    f = schedule_future(io_loop, delay=0)

    @async_generator
    async def gen():
        for i in range(5):
            await yield_(i)

    yielded = []
    async with aclosing(iterate_until(f, gen())) as items:
        async for item in items:
            yielded.append(item)
    assert yielded == list(range(5))
