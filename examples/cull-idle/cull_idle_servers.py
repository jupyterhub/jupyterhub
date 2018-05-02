#!/usr/bin/env python3
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
            'command': 'python3 cull_idle_servers.py --timeout=3600'.split(),
        }
    ]

Or run it manually by generating an API token and storing it in `JUPYTERHUB_API_TOKEN`:

    export JUPYTERHUB_API_TOKEN=`jupyterhub token`
    python3 cull_idle_servers.py [--timeout=900] [--url=http://127.0.0.1:8081/hub/api]

This script uses the same ``--timeout`` and ``--max-age`` values for
culling users and users' servers.  If you want a different value for
users and servers, you should add this script to the services list
twice, just with different ``name``s, different values, and one with
the ``--cull-users`` option.
"""

from datetime import datetime, timezone
from functools import partial
import json
import os

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

import dateutil.parser

from tornado.gen import coroutine, multi
from tornado.locks import Semaphore
from tornado.log import app_log
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.options import define, options, parse_command_line


def parse_date(date_string):
    """Parse a timestamp

    If it doesn't have a timezone, assume utc

    Returned datetime object will always be timezone-aware
    """
    dt = dateutil.parser.parse(date_string)
    if not dt.tzinfo:
        # assume naïve timestamps are UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def format_td(td):
    """
    Nicely format a timedelta object

    as HH:MM:SS
    """
    if td is None:
        return "unknown"
    if isinstance(td, str):
        return td
    seconds = int(td.total_seconds())
    h = seconds // 3600
    seconds = seconds % 3600
    m = seconds // 60
    seconds = seconds % 60
    return "{h:02}:{m:02}:{seconds:02}".format(h=h, m=m, seconds=seconds)


@coroutine
def cull_idle(url, api_token, inactive_limit, cull_users=False, max_age=0, concurrency=10):
    """Shutdown idle single-user servers

    If cull_users, inactive *users* will be deleted as well.
    """
    auth_header = {
        'Authorization': 'token %s' % api_token,
    }
    req = HTTPRequest(
        url=url + '/users',
        headers=auth_header,
    )
    now = datetime.now(timezone.utc)
    client = AsyncHTTPClient()

    if concurrency:
        semaphore = Semaphore(concurrency)
        @coroutine
        def fetch(req):
            """client.fetch wrapped in a semaphore to limit concurrency"""
            yield semaphore.acquire()
            try:
                return (yield client.fetch(req))
            finally:
                yield semaphore.release()
    else:
        fetch = client.fetch

    resp = yield fetch(req)
    users = json.loads(resp.body.decode('utf8', 'replace'))
    futures = []

    @coroutine
    def handle_server(user, server_name, server):
        """Handle (maybe) culling a single server

        Returns True if server is now stopped (user removable),
        False otherwise.
        """
        log_name = user['name']
        if server_name:
            log_name = '%s/%s' % (user['name'], server_name)
        if server.get('pending'):
            app_log.warning(
                "Not culling server %s with pending %s",
                log_name, server['pending'])
            return False

        # jupyterhub < 0.9 defined 'server.url' once the server was ready
        # as an *implicit* signal that the server was ready.
        # 0.9 adds a dedicated, explicit 'ready' field.
        # By current (0.9) definitions, servers that have no pending
        # events and are not ready shouldn't be in the model,
        # but let's check just to be safe.

        if not server.get('ready', bool(server['url'])):
            app_log.warning(
                "Not culling not-ready not-pending server %s: %s",
                log_name, server)
            return False

        if server.get('started'):
            age = now - parse_date(server['started'])
        else:
            # started may be undefined on jupyterhub < 0.9
            age = None

        # check last activity
        # last_activity can be None in 0.9
        if server['last_activity']:
            inactive = now - parse_date(server['last_activity'])
        else:
            # no activity yet, use start date
            # last_activity may be None with jupyterhub 0.9,
            # which introduces the 'started' field which is never None
            # for running servers
            inactive = age

        should_cull = (inactive is not None and
                       inactive.total_seconds() >= inactive_limit)
        if should_cull:
            app_log.info(
                "Culling server %s (inactive for %s)",
                log_name, format_td(inactive))

        if max_age and not should_cull:
            # only check started if max_age is specified
            # so that we can still be compatible with jupyterhub 0.8
            # which doesn't define the 'started' field
            if age is not None and age.total_seconds() >= max_age:
                app_log.info(
                    "Culling server %s (age: %s, inactive for %s)",
                    log_name, format_td(age), format_td(inactive))
                should_cull = True

        if not should_cull:
            app_log.debug(
                "Not culling server %s (age: %s, inactive for %s)",
                log_name, format_td(age), format_td(inactive))
            return False

        req = HTTPRequest(
            url=url + '/users/%s/server' % quote(user['name']),
            method='DELETE',
            headers=auth_header,
        )
        resp = yield fetch(req)
        if resp.code == 202:
            app_log.warning(
                "Server %s is slow to stop",
                log_name,
            )
            # return False to prevent culling user with pending shutdowns
            return False
        return True

    @coroutine
    def handle_user(user):
        """Handle one user.

        Create a list of their servers, and async exec them.  Wait for
        that to be done, and if all servers are stopped, possibly cull
        the user.
        """
        # shutdown servers first.
        # Hub doesn't allow deleting users with running servers.
        # jupyterhub 0.9 always provides a 'servers' model.
        # 0.8 only does this when named servers are enabled.
        if 'servers' in user:
            servers = user['servers']
        else:
            # jupyterhub < 0.9 without named servers enabled.
            # create servers dict with one entry for the default server
            # from the user model.
            # only if the server is running.
            servers = {}
            if user['server']:
                servers[''] = {
                    'last_activity': user['last_activity'],
                    'pending': user['pending'],
                    'url': user['server'],
                }
        server_futures = [
            handle_server(user, server_name, server)
            for server_name, server in servers.items()
        ]
        results = yield multi(server_futures)
        if not cull_users:
            return
        # some servers are still running, cannot cull users
        still_alive = len(results) - sum(results)
        if still_alive:
            app_log.debug(
                "Not culling user %s with %i servers still alive",
                user['name'], still_alive)
            return False

        should_cull = False
        if user.get('created'):
            age = now - parse_date(user['created'])
        else:
            # created may be undefined on jupyterhub < 0.9
            age = None

        # check last activity
        # last_activity can be None in 0.9
        if user['last_activity']:
            inactive = now - parse_date(user['last_activity'])
        else:
            # no activity yet, use start date
            # last_activity may be None with jupyterhub 0.9,
            # which introduces the 'created' field which is never None
            inactive = age

        should_cull = (inactive is not None and
                       inactive.total_seconds() >= inactive_limit)
        if should_cull:
            app_log.info(
                "Culling user %s (inactive for %s)",
                user['name'], inactive)

        if max_age and not should_cull:
            # only check created if max_age is specified
            # so that we can still be compatible with jupyterhub 0.8
            # which doesn't define the 'started' field
            if age is not None and age.total_seconds() >= max_age:
                app_log.info(
                    "Culling user %s (age: %s, inactive for %s)",
                    user['name'], format_td(age), format_td(inactive))
                should_cull = True

        if not should_cull:
            app_log.debug(
                "Not culling user %s (created: %s, last active: %s)",
                user['name'], format_td(age), format_td(inactive))
            return False

        req = HTTPRequest(
            url=url + '/users/%s' % user['name'],
            method='DELETE',
            headers=auth_header,
        )
        yield fetch(req)
        return True

    for user in users:
        futures.append((user['name'], handle_user(user)))

    for (name, f) in futures:
        try:
            result = yield f
        except Exception:
            app_log.exception("Error processing %s", name)
        else:
            if result:
                app_log.debug("Finished culling %s", name)


if __name__ == '__main__':
    define(
        'url',
        default=os.environ.get('JUPYTERHUB_API_URL'),
        help="The JupyterHub API URL",
    )
    define('timeout', default=600, help="The idle timeout (in seconds)")
    define('cull_every', default=0,
           help="The interval (in seconds) for checking for idle servers to cull")
    define('max_age', default=0,
           help="The maximum age (in seconds) of servers that should be culled even if they are active")
    define('cull_users', default=False,
           help="""Cull users in addition to servers.
                This is for use in temporary-user cases such as tmpnb.""",
           )
    define('concurrency', default=10,
           help="""Limit the number of concurrent requests made to the Hub.

                Deleting a lot of users at the same time can slow down the Hub,
                so limit the number of API requests we have outstanding at any given time.
                """
           )

    parse_command_line()
    if not options.cull_every:
        options.cull_every = options.timeout // 2
    api_token = os.environ['JUPYTERHUB_API_TOKEN']

    try:
        AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
    except ImportError as e:
        app_log.warning(
            "Could not load pycurl: %s\n"
            "pycurl is recommended if you have a large number of users.",
            e)

    loop = IOLoop.current()
    cull = partial(
        cull_idle,
        url=options.url,
        api_token=api_token,
        inactive_limit=options.timeout,
        cull_users=options.cull_users,
        max_age=options.max_age,
        concurrency=options.concurrency,
    )
    # schedule first cull immediately
    # because PeriodicCallback doesn't start until the end of the first interval
    loop.add_callback(cull)
    # schedule periodic cull
    pc = PeriodicCallback(cull, 1e3 * options.cull_every)
    pc.start()
    try:
        loop.start()
    except KeyboardInterrupt:
        pass
