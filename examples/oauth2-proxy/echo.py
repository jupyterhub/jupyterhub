"""
A sample service that echoes the request it received,
for illustration purposes.

Listens on 127.0.0.1:9999
"""

import json

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler


class EchoHandler(RequestHandler):
    def get(self):
        self.set_header('content-type', 'application/json')
        self.write(
            json.dumps(
                {
                    "url": self.request.full_url(),
                    "headers": dict(self.request.headers),
                },
                indent=1,
                sort_keys=True,
            )
        )


def main():
    app = Application(
        [
            (r'.*', EchoHandler),
        ]
    )

    http_server = HTTPServer(app)
    http_server.listen(9999, "127.0.0.1")
    IOLoop.current().start()


if __name__ == '__main__':
    main()
