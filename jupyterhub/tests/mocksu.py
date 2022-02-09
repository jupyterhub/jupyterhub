"""Mock single-user server for testing

basic HTTP Server that echos URLs back,
and allow retrieval of sys.argv.

Used by the mock spawners found in `mocking.py` file.

Handlers and their purpose include:

- EchoHandler: echoing URLs back
- ArgsHandler: allowing retrieval of `sys.argv`.

"""
import json
import os
import sys
from urllib.parse import urlparse

from tornado import httpserver
from tornado import ioloop
from tornado import log
from tornado import web
from tornado.options import options

from ..utils import make_ssl_context
from .mockservice import EnvHandler


class EchoHandler(web.RequestHandler):
    def get(self):
        self.write(self.request.path)


class ArgsHandler(web.RequestHandler):
    def get(self):
        self.write(json.dumps(sys.argv))


def main():
    url = urlparse(os.environ["JUPYTERHUB_SERVICE_URL"])
    options.logging = 'debug'
    log.enable_pretty_logging()
    app = web.Application(
        [(r'.*/args', ArgsHandler), (r'.*/env', EnvHandler), (r'.*', EchoHandler)]
    )

    ssl_context = None
    key = os.environ.get('JUPYTERHUB_SSL_KEYFILE') or ''
    cert = os.environ.get('JUPYTERHUB_SSL_CERTFILE') or ''
    ca = os.environ.get('JUPYTERHUB_SSL_CLIENT_CA') or ''

    if key and cert and ca:
        ssl_context = make_ssl_context(key, cert, cafile=ca, check_hostname=False)
        assert url.scheme == "https"

    server = httpserver.HTTPServer(app, ssl_options=ssl_context)
    log.app_log.info(f"Starting mock singleuser server at {url.hostname}:{url.port}")
    server.listen(url.port, url.hostname)
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print('\nInterrupted')


if __name__ == '__main__':
    main()
