from __future__ import annotations

import asyncio
import warnings
from functools import partial
from urllib.parse import unquote
from weakref import WeakKeyDictionary

import aiohttp
from aiohttp import TCPConnector
from aiohttp.client_exceptions import UnixClientConnectorError
from aiohttp.client_proto import ResponseHandler
from aiohttp.helpers import ceil_timeout
from traitlets import Dict
from traitlets.config import SingletonConfigurable


class _HTTPUnixConnector(TCPConnector):
    """Add http+unix support

    automatically routes http+unix to UnixConnector,
    otherwise uses default TCPConnector
    """

    allowed_protocol_schema_set = {"http", "https", "http+unix"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ensure private attributes _factory, _loop are defined
        # which are used in _create_connection
        if not hasattr(self, "_loop"):
            warnings.warn("TCPConnector.__init__ no longer populates private ._loop")
            self._loop = asyncio.get_running_loop()
        if not hasattr(self, "_factory"):
            warnings.warn("TCPConnector.__init__ no longer populates private ._factory")
            self._factory = partial(ResponseHandler, self._loop)

    async def _create_connection(self, req, traces, timeout):
        # this is a _documented_ private method
        # by overriding this instead of connect, it lets us rely on the connection limits,
        # which would be hard to inherit if we override BaseConnector.connect
        if req.url.scheme == "http+unix":
            path = unquote(req.url.host)
            # here copy UnixConnector._create_connection body
            # up-to-date: v3.14.1
            # https://github.com/aio-libs/aiohttp/blob/v3.14.1/aiohttp/connector.py#L1764-L1779
            # License: Apache 2.0

            try:
                async with ceil_timeout(
                    timeout.sock_connect, ceil_threshold=timeout.ceil_threshold
                ):
                    _, proto = await self._loop.create_unix_connection(
                        self._factory, path
                    )
            except OSError as exc:
                if exc.errno is None and isinstance(exc, asyncio.TimeoutError):
                    raise
                raise UnixClientConnectorError(path, req.connection_key, exc) from exc
            return proto
        else:
            # plain http, use unmodified TCP
            return await super()._create_connection(req, traces, timeout)


class JupyterHubHTTPClient(SingletonConfigurable):
    """
    Make HTTP requests.

    This class is used to make intra-JupyterHub requests.

    .. versionadded:: 6.0
    """

    session_options = Dict(
        config=True,
        help="""
        See aiohttp.ClientSession for options to set on the internal HTTP client session.

        Examples include:
        
        - timeout
        """,
    )

    _internal_connector_options = Dict(
        # not config, overrides user options, e.g. internal_ssl options
        help="""
        not configurable internal options for Session
        """
    )
    connector_options = Dict(
        config=True,
        help="""
        See aiohttp.BaseConnector for options to set on the internal HTTP connector.

        Examples include:

        - limit
        - limit_per_host
        - force_close
        """,
    )

    _loop_instances = WeakKeyDictionary()
    __session = None
    _loop = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._loop = asyncio.get_running_loop()
        self.__session = None

    def _new_connector(self):
        options = {}
        options.update(self.connector_options)
        options.update(self._internal_connector_options)
        return _HTTPUnixConnector(**options)

    def _new_session(self):
        global_instance = self.__class__.instance()
        if self is not global_instance:
            # rely on global instance for shared configuration
            return global_instance._new_session()

        options = {}
        options.update(self.session_options)
        options["connector"] = self._new_connector()
        session = aiohttp.ClientSession(**options)
        return session

    @property
    def _has_session(self):
        session = self.__session
        return session is not None and not session.closed

    @property
    def _session(self):
        session = self.__session
        if session and session.closed:
            session = None
        if session is None:
            session = self.__session = self._new_session()
        return session

    async def fetch(self, url, *, method="GET", raise_for_status=True, **kwargs):
        """Make an HTTP request"""
        response = await self._session.request(url=url, method=method, **kwargs)
        if raise_for_status and not response.ok:
            response.raise_for_status()
        return response

    async def close(self):
        """Close and de-register the current client"""
        current_loop = asyncio.get_running_loop()
        if self.__class__._loop_instances.get(current_loop, None) is self:
            self.__class__._loop_instances.pop(current_loop, None)

        if self.__class__.initialized() and self is self.__class__.instance():
            self.__class__.clear_instance()

        if self._has_session:
            await self._session.close()
            self.__session = None

    @classmethod
    def loop_instance(cls):
        # retrieve the global instance for config
        global_instance = cls.instance()
        current_loop = asyncio.get_running_loop()
        if global_instance._loop is current_loop:
            return global_instance

        # but return a per-loop instance
        if current_loop in cls._loop_instances:
            return cls._loop_instances[current_loop]
        instance = cls._loop_instances[current_loop] = cls()
        return instance


async def fetch(url, **kwargs):
    """Make an HTTP request with the shared HTTP Client session

    For accessing JupyterHub internal endpoints.
    """
    return await JupyterHubHTTPClient.loop_instance().fetch(url, **kwargs)
