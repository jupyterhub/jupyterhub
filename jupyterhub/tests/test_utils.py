"""Tests for utilities"""

import asyncio
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

if sys.version_info >= (3, 10):
    from contextlib import aclosing
else:
    from async_generator import aclosing

import pytest
from tornado import gen
from tornado.concurrent import run_on_executor
from tornado.httpserver import HTTPRequest
from tornado.httputil import HTTPHeaders

from .. import utils
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


@pytest.mark.parametrize(
    "forwarded, x_scheme, x_forwarded_proto, expected",
    [
        ("", "", "", "_attr_"),
        ("for=1.2.3.4", "", "", "_attr_"),
        ("for=1.2.3.4,proto=https", "", "", "_attr_"),
        ("", "https", "http", "https"),
        ("", "https, http", "", "https"),
        ("", "https, http", "http", "https"),
        ("proto=http ; for=1.2.3.4, proto=https", "https, http", "", "http"),
        ("proto=invalid;for=1.2.3.4,proto=http", "https, http", "", "https"),
        ("for=1.2.3.4,proto=http", "https, http", "", "https"),
        ("", "invalid, http", "", "_attr_"),
    ],
)
def test_browser_protocol(x_scheme, x_forwarded_proto, forwarded, expected):
    request = Mock(spec=HTTPRequest)
    request.protocol = "_attr_"
    request.headers = HTTPHeaders()
    if x_scheme:
        request.headers["X-Scheme"] = x_scheme
    if x_forwarded_proto:
        request.headers["X-Forwarded-Proto"] = x_forwarded_proto
    if forwarded:
        request.headers["Forwarded"] = forwarded

    proto = utils.get_browser_protocol(request)
    assert proto == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("safe", "safe"),
        ("has--doubledash", "u-hasdoubl--cb052ae"),
        ("uhasdoubl--cb052ae", "u-uhasdoub--3c0d1c9"),
        ("üni", "xn--ni-wka"),
        ("xn--ni-wka", "u-xnniwka--ceb4edd"),
        ("x", "x"),
        ("-pre", "u-pre--0e46e7b"),
        ("É", "u-x--a755f65"),
        ("é", "xn--9ca"),
        ("a" * 64, "u-aaaaaaaa--ffe054f"),
        ("a.b", "u-ab--2e7336d"),
    ],
)
def test_subdomain_hook_idna(name, expected):
    expected_domain = expected + ".domain"
    resolved = utils.subdomain_hook_idna(name, "domain", "user")
    assert resolved == expected_domain


@pytest.mark.parametrize(
    "name, expected",
    [
        ("safe", "safe"),
        ("üni", "_c3_bcni"),
        ("x", "x"),
        ("É", "_c3_89"),
        ("é", "_c3_a9"),
        # bad cases:
        ("a.b", "a.b"),
        ("has--doubledash", "has--doubledash"),
        ("-pre", "-pre"),
        ("a" * 64, "a" * 64),
    ],
)
def test_subdomain_hook_legacy(name, expected):
    expected_domain = expected + ".domain"
    resolved = utils.subdomain_hook_legacy(name, "domain", "user")
    assert resolved == expected_domain


@pytest.mark.parametrize(
    "accept_header, choices, expected",
    [
        (
            "",
            ["application/json"],
            None,
        ),
        (
            "text/html",
            ["application/json"],
            None,
        ),
        (
            "nonsense",
            ["application/json"],
            None,
        ),
        (
            "text/html, application/json",
            ["application/json"],
            "application/json",
        ),
        (
            "text/html, application/json",
            ["application/json", "text/html"],
            "text/html",
        ),
        (
            "text/html; q=0.8, application/json; q=0.9",
            ["application/json", "text/html"],
            "application/json",
        ),
        (
            "text/html, application/json; q=0.9",
            ["application/json", "text/html"],
            "text/html",
        ),
        (
            "text/html; q=notunderstood, application/json; q=0.9",
            ["application/json", "text/html"],
            "text/html",
        ),
    ],
)
def test_get_accepted_mimetype(accept_header, choices, expected):
    accepted = utils.get_accepted_mimetype(accept_header, choices=choices)
    assert accepted == expected
