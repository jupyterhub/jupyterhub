"""Mock single-user server for testing

basic HTTP Server that echos URLs back,
and allow retrieval of sys.argv.
"""

import argparse
import json
import sys

from tornado import web, httpserver, ioloop
from .mockservice import EnvHandler

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
    
    server = httpserver.HTTPServer(app)
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