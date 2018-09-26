from http.server import BaseHTTPRequestHandler, HTTPServer

class DummyServer(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        self.wfile.write(bytes(str(self.server.server_port), "utf-8"))
        
def run(port = 80):
    dummyServer = HTTPServer(("localhost", port), DummyServer)
    print('Starting dummy server...')

    try:
        dummyServer.serve_forever()
    except KeyboardInterrupt:
        pass

    dummyServer.server_close()

if __name__ == "__main__":
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()

