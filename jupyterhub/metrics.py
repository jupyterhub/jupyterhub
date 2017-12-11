"""
Prometheus metrics exported by JupyterHub

Read https://prometheus.io/docs/practices/naming/ for naming
conventions for metrics & labels. We generally prefer naming them
`<noun>_<verb>_<type_suffix>`. So a histogram that's tracking
the duration (in seconds) of servers spawning would be called
SERVER_SPAWN_DURATION_SECONDS.

We also create an Enum for each 'status' type label in every metric
we collect. This is to make sure that the metrics exist regardless
of the condition happening or not. For example, if we don't explicitly
create them, the metric spawn_duration_seconds{status="failure"}
will not actually exist until the first failure. This makes dashboarding
and alerting difficult, so we explicitly list statuses and create
them manually here.
"""
from enum import Enum

from prometheus_client import Histogram

REQUEST_DURATION_SECONDS = Histogram(
    'request_duration_seconds',
    'request duration for all HTTP requests',
    ['method', 'handler', 'code']
)

SERVER_SPAWN_DURATION_SECONDS = Histogram(
    'server_spawn_duration_seconds',
    'time taken for server spawning operation',
    ['status'],
    # Use custom bucket sizes, since the default bucket ranges
    # are meant for quick running processes. Spawns can take a while!
    buckets=[0.5, 1, 2.5, 5, 10, 15, 30, 60, 120, float("inf")]
)

class ServerSpawnStatus(Enum):
    """
    Possible values for 'status' label of SERVER_SPAWN_DURATION_SECONDS
    """
    success = 'success'
    failure = 'failure'
    already_pending = 'already-pending'
    throttled = 'throttled'
    too_many_users = 'too-many-users'

    def __str__(self):
        return self.value

for s in ServerSpawnStatus:
    # Create empty metrics with the given status
    SERVER_SPAWN_DURATION_SECONDS.labels(status=s)


PROXY_ADD_DURATION_SECONDS = Histogram(
    'proxy_add_duration_seconds',
    'duration for adding user routes to proxy',
    ['status']
)

class ProxyAddStatus(Enum):
    """
    Possible values for 'status' label of PROXY_ADD_DURATION_SECONDS
    """
    success = 'success'
    failure = 'failure'

    def __str__(self):
        return self.value

for s in ProxyAddStatus:
    PROXY_ADD_DURATION_SECONDS.labels(status=s)

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
