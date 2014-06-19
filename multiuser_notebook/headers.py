import json

from tornado import web
from tornado.escape import xhtml_escape

class HeadersHandler(web.RequestHandler):
    def get(self):
        headers = {}
        for key, value in self.request.headers.items():
            if ';' in value:
                value = [ s.strip() for s in value.split(';') ]
            headers[key] = value
        self.write("<pre>%s</pre>" % (
            xhtml_escape(json.dumps(headers, indent=1))
        ))
    
