from concurrent.futures import ThreadPoolExecutor
import requests

class _AsyncRequests:
    """Wrapper around requests to return a Future from request methods
    
    A single thread is allocated to avoid blocking the IOLoop thread.
    """
    def __init__(self):
        self.executor = ThreadPoolExecutor(1)

    def __getattr__(self, name):
        requests_method = getattr(requests, name)
        return lambda *args, **kwargs: self.executor.submit(requests_method, *args, **kwargs)

# async_requests.get = requests.get returning a Future, etc.
async_requests = _AsyncRequests()

