"""
Prometheus metrics exported by JupyterHub
"""
from prometheus_client import Histogram

REQUEST_DURATION_SECONDS = Histogram(
    'request_duration_seconds',
    'request duration for all HTTP requests',
    ['method', 'handler', 'code']
)

def prometheus_log_method(handler):
    """
    Tornado log handler for recording RED metrics

    We record the following metrics:
       Rate – the number of requests, per second, your services are serving.
       Errors – the number of failed requests per second.
       Duration – The amount of time each request takes expressed as a time interval.

    We use a fully qualified name of the handler as a label,
    rather than every url path to reduce cardinality.
    """
    REQUEST_DURATION_SECONDS.labels(
        method=handler.request.method,
        handler='{}.{}'.format(handler.__class__.__module__, type(handler).__name__),
        code=handler.get_status()
    ).observe(handler.request.request_time())
