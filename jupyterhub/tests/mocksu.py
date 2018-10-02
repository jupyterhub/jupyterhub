"""Mock single-user server for testing

basic HTTP Server that echos URLs back,
and allow retrieval of sys.argv.

Used by the mock spawners found in `mocking.py` file.

Handlers and their purpose include:

- EchoHandler: echoing URLs back
- ArgsHandler: allowing retrieval of `sys.argv`.

"""
import argparse
import json
import sys
import os

from tornado import web, httpserver, ioloop
from .mockservice import EnvHandler
from ..utils import make_ssl_context

class EchoHandler(web.RequestHandler):
    def get(self):
        self.write(self.request.path)

class ArgsHandler(web.RequestHandler):
    def get(self):
        self.write(json.dumps(sys.argv))

def main(args):

    app = web.Application([
        (r'.*/args', ArgsHandler),
        (r'.*/env', EnvHandler),
        (r'.*', EchoHandler),
    ])
    
    ssl_context = None
    key = os.environ.get('JUPYTERHUB_NOTEBOOK_SSL_KEYFILE') or ''
    cert = os.environ.get('JUPYTERHUB_NOTEBOOK_SSL_CERTFILE') or ''
    ca = os.environ.get('JUPYTERHUB_NOTEBOOK_SSL_CLIENT_CA') or ''

    if key and cert and ca:
        ssl_context = make_ssl_context(
            key,
            cert,
            cafile = ca,
            check_hostname = False
        )

    server = httpserver.HTTPServer(app, ssl_options=ssl_context)
    server.listen(args.port)
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print('\nInterrupted')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int)
    args, extra = parser.parse_known_args()
    main(args)
