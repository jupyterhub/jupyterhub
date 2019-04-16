import asyncio
from concurrent.futures import ThreadPoolExecutor

import requests
from certipy import Certipy

from jupyterhub import orm
from jupyterhub.objects import Server
from jupyterhub.utils import url_path_join as ujoin


class _AsyncRequests:
    """Wrapper around requests to return a Future from request methods

    A single thread is allocated to avoid blocking the IOLoop thread.
    """

    def __init__(self):
        self.executor = ThreadPoolExecutor(1)
        real_submit = self.executor.submit
        self.executor.submit = lambda *args, **kwargs: asyncio.wrap_future(
            real_submit(*args, **kwargs)
        )

    def __getattr__(self, name):
        requests_method = getattr(requests, name)
        return lambda *args, **kwargs: self.executor.submit(
            requests_method, *args, **kwargs
        )


# async_requests.get = requests.get returning a Future, etc.
async_requests = _AsyncRequests()


class AsyncSession(requests.Session):
    """requests.Session object that runs in the background thread"""

    def request(self, *args, **kwargs):
        return async_requests.executor.submit(super().request, *args, **kwargs)


def ssl_setup(cert_dir, authority_name):
    # Set up the external certs with the same authority as the internal
    # one so that certificate trust works regardless of chosen endpoint.
    certipy = Certipy(store_dir=cert_dir)
    alt_names = ["DNS:localhost", "IP:127.0.0.1"]
    internal_authority = certipy.create_ca(authority_name, overwrite=True)
    external_certs = certipy.create_signed_pair(
        "external", authority_name, overwrite=True, alt_names=alt_names
    )
    return external_certs


def check_db_locks(func):
    """Decorator that verifies no locks are held on database upon exit.

    This decorator for test functions verifies no locks are held on the
    application's database upon exit by creating and dropping a dummy table.

    The decorator relies on an instance of JupyterHubApp being the first
    argument to the decorated function.

    Example
    -------

        @check_db_locks
        def api_request(app, *api_path, **kwargs):

    """

    def new_func(app, *args, **kwargs):
        retval = func(app, *args, **kwargs)

        temp_session = app.session_factory()
        temp_session.execute('CREATE TABLE dummy (foo INT)')
        temp_session.execute('DROP TABLE dummy')
        temp_session.close()

        return retval

    return new_func


def find_user(db, name, app=None):
    """Find user in database."""
    orm_user = db.query(orm.User).filter(orm.User.name == name).first()
    if app is None:
        return orm_user
    else:
        return app.users[orm_user.id]


def add_user(db, app=None, **kwargs):
    """Add a user to the database."""
    orm_user = find_user(db, name=kwargs.get('name'))
    if orm_user is None:
        orm_user = orm.User(**kwargs)
        db.add(orm_user)
    else:
        for attr, value in kwargs.items():
            setattr(orm_user, attr, value)
    db.commit()
    if app:
        return app.users[orm_user.id]
    else:
        return orm_user


def auth_header(db, name):
    """Return header with user's API authorization token."""
    user = find_user(db, name)
    if user is None:
        user = add_user(db, name=name)
    token = user.new_api_token()
    return {'Authorization': 'token %s' % token}


@check_db_locks
async def api_request(
    app, *api_path, method='get', noauth=False, bypass_proxy=False, **kwargs
):
    """Make an API request"""
    if bypass_proxy:
        # make a direct request to the hub,
        # skipping the proxy
        base_url = app.hub.url
    else:
        base_url = public_url(app, path='hub')
    headers = kwargs.setdefault('headers', {})

    if 'Authorization' not in headers and not noauth and 'cookies' not in kwargs:
        # make a copy to avoid modifying arg in-place
        kwargs['headers'] = h = {}
        h.update(headers)
        h.update(auth_header(app.db, kwargs.pop('name', 'admin')))

    if 'cookies' in kwargs:
        # for cookie-authenticated requests,
        # set Referer so it looks like the request originated
        # from a Hub-served page
        headers.setdefault('Referer', ujoin(base_url, 'test'))

    url = ujoin(base_url, 'api', *api_path)
    f = getattr(async_requests, method)
    if app.internal_ssl:
        kwargs['cert'] = (app.internal_ssl_cert, app.internal_ssl_key)
        kwargs["verify"] = app.internal_ssl_ca
    resp = await f(url, **kwargs)
    assert "frame-ancestors 'self'" in resp.headers['Content-Security-Policy']
    assert (
        ujoin(app.hub.base_url, "security/csp-report")
        in resp.headers['Content-Security-Policy']
    )
    assert 'http' not in resp.headers['Content-Security-Policy']
    if not kwargs.get('stream', False) and resp.content:
        assert resp.headers.get('content-type') == 'application/json'
    return resp


def get_page(path, app, hub=True, **kw):
    if "://" in path:
        raise ValueError(
            "Not a hub page path: %r. Did you mean async_requests.get?" % path
        )
    if hub:
        prefix = app.hub.base_url
    else:
        prefix = app.base_url
    base_url = ujoin(public_host(app), prefix)
    return async_requests.get(ujoin(base_url, path), **kw)


def public_host(app):
    """Return the public *host* (no URL prefix) of the given JupyterHub instance."""
    if app.subdomain_host:
        return app.subdomain_host
    else:
        return Server.from_url(app.proxy.public_url).host


def public_url(app, user_or_service=None, path=''):
    """Return the full, public base URL (including prefix) of the given JupyterHub instance."""
    if user_or_service:
        if app.subdomain_host:
            host = user_or_service.host
        else:
            host = public_host(app)
        prefix = user_or_service.prefix
    else:
        host = public_host(app)
        prefix = Server.from_url(app.proxy.public_url).base_url
    if path:
        return host + ujoin(prefix, path)
    else:
        return host + prefix
