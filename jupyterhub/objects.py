"""Some general objects for use in JupyterHub"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import socket
from urllib.parse import urlparse

from tornado import gen

from traitlets import (
    HasTraits, Instance, Integer, Unicode,
    default, observe,
)
from . import orm
from .utils import (
    url_path_join, can_connect, wait_for_server,
    wait_for_http_server, random_port,
)

class Server(HasTraits):
    """An object representing an HTTP endpoint.

    *Some* of these reside in the database (user servers),
    but others (Hub, proxy) are in-memory only.
    """
    orm_server = Instance(orm.Server, allow_none=True)

    ip = Unicode()
    connect_ip = Unicode()
    proto = Unicode('http')
    port = Integer()
    base_url = Unicode('/')
    cookie_name = Unicode('')
    
    @default('connect_ip')
    def _default_connect_ip(self):
        # if listening on all interfaces, default to hostname
        if self.ip in {'', '0.0.0.0'}:
            return socket.gethostname()
        return self.ip

    @classmethod
    def from_url(cls, url):
        """Create a Server from a given URL"""
        urlinfo = urlparse(url)
        proto = urlinfo.scheme
        ip = urlinfo.hostname or ''
        port = urlinfo.port
        if not port:
            if proto == 'https':
                port = 443
            else:
                port = 80
        return cls(proto=proto, ip=ip, port=port, base_url=urlinfo.path)

    @default('port')
    def _default_port(self):
        return random_port()

    @observe('orm_server')
    def _orm_server_changed(self, change):
        """When we get an orm_server, get attributes from there."""
        obj = change.new
        self.proto = obj.proto
        self.ip = obj.ip
        self.port = obj.port
        self.base_url = obj.base_url
        self.cookie_name = obj.cookie_name

    # setter to pass through to the database
    @observe('ip', 'proto', 'port', 'base_url', 'cookie_name')
    def _change(self, change):
        if self.orm_server:
            setattr(self.orm_server, change.name, change.new)

    @property
    def host(self):
        return "{proto}://{ip}:{port}".format(
            proto=self.proto,
            ip=self.connect_ip,
            port=self.port,
        )

    @property
    def url(self):
        return "{host}{uri}".format(
            host=self.host,
            uri=self.base_url,
        )

    @property
    def bind_url(self):
        """representation of URL used for binding

        Never used in APIs, only logging,
        since it can be non-connectable value, such as '', meaning all interfaces.
        """
        if self.ip in {'', '0.0.0.0'}:
            return self.url.replace('127.0.0.1', self.ip or '*', 1)
        return self.url

    @gen.coroutine
    def wait_up(self, timeout=10, http=False):
        """Wait for this server to come up"""
        if http:
            yield wait_for_http_server(self.url, timeout=timeout)
        else:
            yield wait_for_server(self.connect_ip, self.port, timeout=timeout)

    def is_up(self):
        """Is the server accepting connections?"""
        return can_connect(self.ip or '127.0.0.1', self.port)


class Hub(Server):
    """Bring it all together at the hub.

    The Hub is a server, plus its API path suffix

    the api_url is the full URL plus the api_path suffix on the end
    of the server base_url.
    """

    @property
    def server(self):
        """backward-compat"""
        return self
    public_host = Unicode()

    @property
    def api_url(self):
        """return the full API url (with proto://host...)"""
        return url_path_join(self.url, 'api')

    def __repr__(self):
        return "<%s %s:%s>" % (
            self.__class__.__name__, self.server.ip, self.server.port,
        )
