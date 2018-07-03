"""Some general objects for use in JupyterHub"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import socket
from urllib.parse import urlparse, urlunparse
import warnings

from traitlets import (
    HasTraits, Instance, Integer, Unicode,
    default, observe, validate,
)
from .traitlets import URLPrefix
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
    connect_port = Integer()
    proto = Unicode('http')
    port = Integer()
    base_url = URLPrefix('/')
    cookie_name = Unicode('')
    connect_url = Unicode('')
    bind_url = Unicode('')

    @default('bind_url')
    def bind_url_default(self):
        """representation of URL used for binding

        Never used in APIs, only logging,
        since it can be non-connectable value, such as '', meaning all interfaces.
        """
        if self.ip in {'', '0.0.0.0'}:
            return self.url.replace(self._connect_ip, self.ip or '*', 1)
        return self.url

    @observe('bind_url')
    def _bind_url_changed(self, change):
        urlinfo = urlparse(change.new)
        self.proto = urlinfo.scheme
        self.ip = urlinfo.hostname or ''
        port = urlinfo.port
        if port is None:
            if self.proto == 'https':
                port = 443
            else:
                port = 80
        self.port = port

    @validate('connect_url')
    def _connect_url_add_prefix(self, proposal):
        """Ensure connect_url includes base_url"""
        if not proposal.value:
            # Don't add the prefix if the setting is being cleared
            return proposal.value
        urlinfo = urlparse(proposal.value)
        if not urlinfo.path.startswith(self.base_url):
            urlinfo = urlinfo._replace(path=self.base_url)
            return urlunparse(urlinfo)
        return proposal.value

    @property
    def _connect_ip(self):
        """The address to use when connecting to this server

        When `ip` is set to a real ip address, the same value is used.
        When `ip` refers to 'all interfaces' (e.g. '0.0.0.0'),
        clients connect via hostname by default.
        Setting `connect_ip` explicitly overrides any default behavior.
        """
        if self.connect_ip:
            return self.connect_ip
        elif self.ip in {'', '0.0.0.0'}:
            # if listening on all interfaces, default to hostname for connect
            return socket.gethostname()
        else:
            return self.ip

    @property
    def _connect_port(self):
        """
        The port to use when connecting to this server.

        Defaults to self.port, but can be overridden by setting self.connect_port
        """
        if self.connect_port:
            return self.connect_port
        return self.port

    @classmethod
    def from_orm(cls, orm_server):
        """Create a server from an orm.Server"""
        return cls(orm_server=orm_server)

    @classmethod
    def from_url(cls, url):
        """Create a Server from a given URL"""
        return cls(bind_url=url, base_url=urlparse(url).path)

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
        if self.orm_server and getattr(self.orm_server, change.name) != change.new:
            # setattr on an sqlalchemy object sets the dirty flag,
            # even if the value doesn't change.
            # Avoid calling setattr when there's been no change,
            # to avoid setting the dirty flag and triggering rollback.
            setattr(self.orm_server, change.name, change.new)

    @property
    def host(self):
        if self.connect_url:
            parsed = urlparse(self.connect_url)
            return "{proto}://{host}".format(
                proto=parsed.scheme,
                host=parsed.netloc,
            )
        return "{proto}://{ip}:{port}".format(
            proto=self.proto,
            ip=self._connect_ip,
            port=self._connect_port,
        )

    @property
    def url(self):
        if self.connect_url:
            return self.connect_url
        return "{host}{uri}".format(
            host=self.host,
            uri=self.base_url,
        )

    def wait_up(self, timeout=10, http=False):
        """Wait for this server to come up"""
        if http:
            return wait_for_http_server(self.url, timeout=timeout)
        else:
            return wait_for_server(self._connect_ip, self._connect_port, timeout=timeout)

    def is_up(self):
        """Is the server accepting connections?"""
        return can_connect(self._connect_ip, self._connect_port)


class Hub(Server):
    """Bring it all together at the hub.

    The Hub is a server, plus its API path suffix

    the api_url is the full URL plus the api_path suffix on the end
    of the server base_url.
    """

    cookie_name = 'jupyterhub-hub-login'

    @property
    def server(self):
        warnings.warn("Hub.server is deprecated in JupyterHub 0.8. Access attributes on the Hub directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self
    public_host = Unicode()
    routespec = Unicode()

    @property
    def api_url(self):
        """return the full API url (with proto://host...)"""
        return url_path_join(self.url, 'api')

    def __repr__(self):
        return "<%s %s:%s>" % (
            self.__class__.__name__, self.server.ip, self.server.port,
        )
