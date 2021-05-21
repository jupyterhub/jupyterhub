"""An example service authenticating with the Hub.

This serves `/services/whoami-api/`, authenticated with the Hub, showing the user their own info.

HubAuthenticated only supports token-based access.
"""
import json
import os
from urllib.parse import urlparse

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application
from tornado.web import authenticated
from tornado.web import RequestHandler

from jupyterhub.services.auth import HubAuthenticated


class WhoAmIHandler(HubAuthenticated, RequestHandler):
    @authenticated
    def get(self):
        user_model = self.get_current_user()
        self.set_header('content-type', 'application/json')
        self.write(json.dumps(user_model, indent=1, sort_keys=True))


def main():
    app = Application(
        [
            (os.environ['JUPYTERHUB_SERVICE_PREFIX'] + '/?', WhoAmIHandler),
            (r'.*', WhoAmIHandler),
        ]
    )

    http_server = HTTPServer(app)
    url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])

    http_server.listen(url.port, url.hostname)

    IOLoop.current().start()


if __name__ == '__main__':
    main()
