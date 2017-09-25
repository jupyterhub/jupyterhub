"""
Task :  Web service for Cull UI

Date : 16 Aug 2016

Version : 1.0

Author : Vigneshwer
"""

# Loading python modules 
import tornado.ioloop
import tornado.web
import tornado.escape
from tornado.concurrent import Future
from tornado.gen import coroutine
from tornado.options import define, options, parse_command_line
from tornado.log import app_log
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
import tornado.websocket
import config
import datetime
import json
import os
import datetime
from dateutil.parser import parse as parse_date 
import json

define("port", default=8888, help="run on the given port", type=int)
define("debug", default=False, help="run in debug mode")
define("static_path", default="./", help="Content of the template")
define('url', default='https://127.0.0.1:443/hub', help="The JupyterHub API URL")

# Values to be changed
api_token="c4297f02c25b49c2a63c9b102b24cc51"
url = 'https://127.0.0.1:443/hub'
certi_loc='./certs/jupyterhub.crt'
cull_time=1000

# Constant variables
clients = [] 
session_info={}
time_out_val=None

# Renders the index page
class MainHandler(tornado.web.RequestHandler):
	@coroutine
	def get(self):
		data=False
		self.render("index.html", title="Cull service UI", data=data)

# Gets and post data to the UI contiounsly with web socket and starts cull service
class WebSocketHandler(tornado.websocket.WebSocketHandler):
	def open(self):
		print 'new connection'
		if self not in clients:
			clients.append(self)
		dummy_data=json.dumps({"no user":"Cull Not started"})
		self.write_message(str(dummy_data))
	
	def on_message(self, message):
		print 'tornado received from client: %s' % message
		time_out_val=int(message)
		periodic_callback = tornado.ioloop.PeriodicCallback(lambda: cull_service(time_out_val),cull_time)
		print "Starteedperiodic call back started"
		periodic_callback.start()

	def on_close(self):
		print 'connection closed'
		if self not in clients:
			clients.remove(self)

# Asyn cull service
@coroutine
def cull_service(time_out):
	auth_header = {'Authorization': 'token %s' % api_token}
	req = HTTPRequest(url=url + '/api/users',headers=auth_header, ca_certs=certi_loc,)
	http = AsyncHTTPClient()
	resp = yield http.fetch(req)
	
	now = datetime.datetime.utcnow()
	cull_limit = now - datetime.timedelta(seconds=time_out)
	print "Cull limit is :-" +str(cull_limit)

	if resp.error or resp == None: 
		raise tornado.web.HTTPError(500)
	else:
		get_resp = json.loads(resp.body.decode('utf8', 'replace'))
		# print "Response from api :- " +str(get_resp)
		futures = []
		for user in get_resp:
			last_activity = parse_date(user['last_activity'])
			if user['server'] and last_activity < cull_limit:
				req = HTTPRequest(url=url + '/api/users/%s/server' % user['name'],method='DELETE',headers=auth_header,ca_certs=certi_loc,)
				print "Culling %s (inactive since %s)", user['name'], last_activity
				app_log.info("Culling %s (inactive since %s)", user['name'], last_activity)
				futures.append((user['name'], http.fetch(req)))
			elif user['server'] and last_activity > cull_limit:
				uname=	user['name']
				session_info[str(uname)]=str(last_activity)
				print "Not culling %s (active since %s)", user['name'], last_activity
				app_log.debug("Not culling %s (active since %s)", user['name'], last_activity)
		for (name,f) in futures:
			yield f
			print "Finished Culling %s",name
			app_log.debug("Finished Culling %s",name)

	json_session_data = json.dumps(session_info)
	# print session_info
	# print "Json data :" + str(json_session_data)
	for queues in clients:
		queues.write_message(str(json_session_data))

# Stops the tornadi web server
class StopTornado(tornado.web.RequestHandler):
    def get(self):
        tornado.ioloop.IOLoop.instance().stop()

if __name__ == "__main__":
	# Routes
    app = tornado.web.Application([
    	(r"/", MainHandler),
    	(r"/KillTornado", StopTornado),
    	(r"/ws", WebSocketHandler)],
    	debug=options.debug,
    	static_path=options.static_path,
    	)
    app.listen(options.port)
    print "Server started at 127.0.0.1:8888"
    # Starts the webserer
    tornado.ioloop.IOLoop.instance().start()
 