"""Mock service for testing

basic HTTP Server that echos URLs back,
and allow retrieval of sys.argv.
"""

import argparse
import json
import os
import sys
from urllib.parse import urlparse

import requests
from tornado import web, httpserver, ioloop

from jupyterhub.services.auth import  HubAuthenticated

class EchoHandler(web.RequestHandler):
    def get(self):
        self.write(self.request.path)


class EnvHandler(web.RequestHandler):
    def get(self):
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(dict(os.environ)))


class APIHandler(web.RequestHandler):
    def get(self, path):
        api_token = os.environ['JUPYTERHUB_API_TOKEN']
        api_url = os.environ['JUPYTERHUB_API_URL']
        r = requests.get(api_url + path, headers={
            'Authorization': 'token %s' % api_token
        })
        r.raise_for_status()
        self.set_header('Content-Type', 'application/json')
        self.write(r.text)

class WhoAmIHandler(HubAuthenticated, web.RequestHandler):

    @web.authenticated
    def get(self):
        self.write(self.get_current_user())


def main():
    if os.environ['JUPYTERHUB_SERVICE_URL']:
        url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])
        app = web.Application([
            (r'.*/env', EnvHandler),
            (r'.*/api/(.*)', APIHandler),
            (r'.*/whoami/?', WhoAmIHandler),
            (r'.*', EchoHandler),
        ])

        server = httpserver.HTTPServer(app)
        server.listen(url.port, url.hostname)
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print('\nInterrupted')

if __name__ == '__main__':
    from tornado.options import parse_command_line
    parse_command_line()
    main()
