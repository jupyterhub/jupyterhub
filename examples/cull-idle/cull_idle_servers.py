#!/usr/bin/env python
"""script to monitor and cull idle single-user servers

Caveats:

last_activity is not updated with high frequency,
so cull timeout should be greater than the sum of:

- single-user websocket ping interval (default: 30s)
- JupyterHub.last_activity_interval (default: 5 minutes)

You can run this as a service managed by JupyterHub with this in your config::


    c.JupyterHub.services = [
        {
            'name': 'cull-idle',
            'admin': True,
            'command': 'python cull_idle_servers.py --timeout=3600'.split(),
        }
    ]

Or run it manually by generating an API token and storing it in `JUPYTERHUB_API_TOKEN`:

    export JUPYTERHUB_API_TOKEN=`jupyterhub token`
    python cull_idle_servers.py [--timeout=900] [--url=http://127.0.0.1:8081/hub/api]
"""

import datetime
import json
import os

from dateutil.parser import parse as parse_date

from tornado.gen import coroutine
from tornado.log import app_log
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.options import define, options, parse_command_line


@coroutine
def cull_idle(url, api_token, timeout):
    """cull idle single-user servers"""
    auth_header = {
            'Authorization': 'token %s' % api_token
        }
    req = HTTPRequest(url=url + '/users',
        headers=auth_header,
    )
    now = datetime.datetime.utcnow()
    cull_limit = now - datetime.timedelta(seconds=timeout)
    client = AsyncHTTPClient()
    resp = yield client.fetch(req)
    users = json.loads(resp.body.decode('utf8', 'replace'))
    futures = []
    for user in users:
        last_activity = parse_date(user['last_activity'])
        if user['server'] and last_activity < cull_limit:
            app_log.info("Culling %s (inactive since %s)", user['name'], last_activity)
            req = HTTPRequest(url=url + '/users/%s/server' % user['name'],
                method='DELETE',
                headers=auth_header,
            )
            futures.append((user['name'], client.fetch(req)))
        elif user['server'] and last_activity > cull_limit:
            app_log.debug("Not culling %s (active since %s)", user['name'], last_activity)
    
    for (name, f) in futures:
        yield f
        app_log.debug("Finished culling %s", name)

if __name__ == '__main__':
    define('url', default=os.environ.get('JUPYTERHUB_API_URL'), help="The JupyterHub API URL")
    define('timeout', default=600, help="The idle timeout (in seconds)")
    define('cull_every', default=0, help="The interval (in seconds) for checking for idle servers to cull")
    
    parse_command_line()
    if not options.cull_every:
        options.cull_every = options.timeout // 2
    
    api_token = os.environ['JUPYTERHUB_API_TOKEN']
    
    loop = IOLoop.current()
    cull = lambda : cull_idle(options.url, api_token, options.timeout)
    # run once before scheduling periodic call
    loop.run_sync(cull)
    # schedule periodic cull
    pc = PeriodicCallback(cull, 1e3 * options.cull_every)
    pc.start()
    try:
        loop.start()
    except KeyboardInterrupt:
        pass
    