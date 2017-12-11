"""
Prometheus metrics exported by JupyterHub

Read https://prometheus.io/docs/practices/naming/ for naming
conventions for metrics & labels.
"""
from prometheus_client import Histogram

REQUEST_DURATION_SECONDS = Histogram(
    'request_duration_seconds',
    'request duration for all HTTP requests',
    ['method', 'handler', 'code']
)

SPAWN_DURATION_SECONDS = Histogram(
    'spawn_duration_seconds',
    'spawn duration for all server spawns',
    ['status'],
    # Use custom bucket sizes, since the default bucket ranges
    # are meant for quick running processes. Spawns can take a while!
    buckets=[0.5, 1, 2.5, 5, 10, 15, 30, 60, 120, float("inf")]
)

PROXY_ADD_DURATION_SECONDS = Histogram(
    'proxy_add_duration_seconds',
    'duration for adding user routes to proxy',
    ['status']
)

def prometheus_log_method(handler):
    """
    Tornado log handler for recording RED metrics.

    We record the following metrics:
       Rate – the number of requests, per second, your services are serving.
       Errors – the number of failed requests per second.
       Duration – The amount of time each request takes expressed as a time interval.

    We use a fully qualified name of the handler as a label,
    rather than every url path to reduce cardinality.

    This function should be either the value of or called from a function
    that is the 'log_function' tornado setting. This makes it get called
    at the end of every request, allowing us to record the metrics we need.
    """
    REQUEST_DURATION_SECONDS.labels(
        method=handler.request.method,
        handler='{}.{}'.format(handler.__class__.__module__, type(handler).__name__),
        code=handler.get_status()
    ).observe(handler.request.request_time())
