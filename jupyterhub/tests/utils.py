import asyncio
from concurrent.futures import ThreadPoolExecutor

from certipy import Certipy
import requests


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
