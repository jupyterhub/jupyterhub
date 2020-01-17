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

from prometheus_client import Gauge
from prometheus_client import Histogram

REQUEST_DURATION_SECONDS = Histogram(
    'request_duration_seconds',
    'request duration for all HTTP requests',
    ['method', 'handler', 'code'],
)

SERVER_SPAWN_DURATION_SECONDS = Histogram(
    'server_spawn_duration_seconds',
    'time taken for server spawning operation',
    ['status'],
    # Use custom bucket sizes, since the default bucket ranges
    # are meant for quick running processes. Spawns can take a while!
    buckets=[0.5, 1, 2.5, 5, 10, 15, 30, 60, 120, float("inf")],
)

RUNNING_SERVERS = Gauge(
    'running_servers', 'the number of user servers currently running'
)

TOTAL_USERS = Gauge('total_users', 'total number of users')

CHECK_ROUTES_DURATION_SECONDS = Histogram(
    'check_routes_duration_seconds', 'Time taken to validate all routes in proxy'
)

HUB_STARTUP_DURATION_SECONDS = Histogram(
    'hub_startup_duration_seconds', 'Time taken for Hub to start'
)

INIT_SPAWNERS_DURATION_SECONDS = Histogram(
    'init_spawners_duration_seconds', 'Time taken for spawners to initialize'
)

PROXY_POLL_DURATION_SECONDS = Histogram(
    'proxy_poll_duration_seconds', 'duration for polling all routes from proxy'
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
    'proxy_add_duration_seconds', 'duration for adding user routes to proxy', ['status']
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


SERVER_POLL_DURATION_SECONDS = Histogram(
    'server_poll_duration_seconds',
    'time taken to poll if server is running',
    ['status'],
)


class ServerPollStatus(Enum):
    """
    Possible values for 'status' label of SERVER_POLL_DURATION_SECONDS
    """

    running = 'running'
    stopped = 'stopped'

    @classmethod
    def from_status(cls, status):
        """Return enum string for a given poll status"""
        if status is None:
            return cls.running
        return cls.stopped


for s in ServerPollStatus:
    SERVER_POLL_DURATION_SECONDS.labels(status=s)


SERVER_STOP_DURATION_SECONDS = Histogram(
    'server_stop_seconds', 'time taken for server stopping operation', ['status']
)


class ServerStopStatus(Enum):
    """
    Possible values for 'status' label of SERVER_STOP_DURATION_SECONDS
    """

    success = 'success'
    failure = 'failure'

    def __str__(self):
        return self.value


for s in ServerStopStatus:
    SERVER_STOP_DURATION_SECONDS.labels(status=s)


PROXY_DELETE_DURATION_SECONDS = Histogram(
    'proxy_delete_duration_seconds',
    'duration for deleting user routes from proxy',
    ['status'],
)


class ProxyDeleteStatus(Enum):
    """
    Possible values for 'status' label of PROXY_DELETE_DURATION_SECONDS
    """

    success = 'success'
    failure = 'failure'

    def __str__(self):
        return self.value


for s in ProxyDeleteStatus:
    PROXY_DELETE_DURATION_SECONDS.labels(status=s)


def prometheus_log_method(handler):
    """
    Tornado log handler for recording RED metrics.

    We record the following metrics:
       Rate: the number of requests, per second, your services are serving.
       Errors: the number of failed requests per second.
       Duration: the amount of time each request takes expressed as a time interval.

    We use a fully qualified name of the handler as a label,
    rather than every url path to reduce cardinality.

    This function should be either the value of or called from a function
    that is the 'log_function' tornado setting. This makes it get called
    at the end of every request, allowing us to record the metrics we need.
    """
    REQUEST_DURATION_SECONDS.labels(
        method=handler.request.method,
        handler='{}.{}'.format(handler.__class__.__module__, type(handler).__name__),
        code=handler.get_status(),
    ).observe(handler.request.request_time())
