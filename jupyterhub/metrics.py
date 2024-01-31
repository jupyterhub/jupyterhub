"""
Prometheus metrics exported by JupyterHub

Read https://prometheus.io/docs/practices/naming/ for naming
conventions for metrics & labels. We generally prefer naming them
`jupyterhub_<noun>_<verb>_<type_suffix>`. So a histogram that's tracking
the duration (in seconds) of servers spawning would be called
jupyterhub_server_spawn_duration_seconds.

We also create an Enum for each 'status' type label in every metric
we collect. This is to make sure that the metrics exist regardless
of the condition happening or not. For example, if we don't explicitly
create them, the metric spawn_duration_seconds{status="failure"}
will not actually exist until the first failure. This makes dashboarding
and alerting difficult, so we explicitly list statuses and create
them manually here.

.. versionchanged:: 1.3

    added ``jupyterhub_`` prefix to metric names.
"""

from datetime import timedelta
from enum import Enum

from prometheus_client import Gauge, Histogram
from tornado.ioloop import PeriodicCallback
from traitlets import Any, Bool, Integer
from traitlets.config import LoggingConfigurable

from . import orm
from .utils import utcnow

REQUEST_DURATION_SECONDS = Histogram(
    'jupyterhub_request_duration_seconds',
    'request duration for all HTTP requests',
    ['method', 'handler', 'code'],
)

SERVER_SPAWN_DURATION_SECONDS = Histogram(
    'jupyterhub_server_spawn_duration_seconds',
    'time taken for server spawning operation',
    ['status'],
    # Use custom bucket sizes, since the default bucket ranges
    # are meant for quick running processes. Spawns can take a while!
    buckets=[0.5, 1, 2.5, 5, 10, 15, 30, 60, 120, 180, 300, 600, float("inf")],
)

RUNNING_SERVERS = Gauge(
    'jupyterhub_running_servers', 'the number of user servers currently running'
)

TOTAL_USERS = Gauge('jupyterhub_total_users', 'total number of users')

ACTIVE_USERS = Gauge(
    'jupyterhub_active_users',
    'number of users who were active in the given time period',
    ['period'],
)

CHECK_ROUTES_DURATION_SECONDS = Histogram(
    'jupyterhub_check_routes_duration_seconds',
    'Time taken to validate all routes in proxy',
)

HUB_STARTUP_DURATION_SECONDS = Histogram(
    'jupyterhub_hub_startup_duration_seconds', 'Time taken for Hub to start'
)

INIT_SPAWNERS_DURATION_SECONDS = Histogram(
    'jupyterhub_init_spawners_duration_seconds', 'Time taken for spawners to initialize'
)

PROXY_POLL_DURATION_SECONDS = Histogram(
    'jupyterhub_proxy_poll_duration_seconds',
    'duration for polling all routes from proxy',
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
    'jupyterhub_proxy_add_duration_seconds',
    'duration for adding user routes to proxy',
    ['status'],
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
    'jupyterhub_server_poll_duration_seconds',
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
    'jupyterhub_server_stop_seconds',
    'time taken for server stopping operation',
    ['status'],
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
    'jupyterhub_proxy_delete_duration_seconds',
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


class ActiveUserPeriods(Enum):
    """
    Possible values for 'period' label of ACTIVE_USERS
    """

    twenty_four_hours = '24h'
    seven_days = '7d'
    thirty_days = '30d'


for s in ActiveUserPeriods:
    ACTIVE_USERS.labels(period=s.value)


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
        handler=f'{handler.__class__.__module__}.{type(handler).__name__}',
        code=handler.get_status(),
    ).observe(handler.request.request_time())


class PeriodicMetricsCollector(LoggingConfigurable):
    """
    Collect metrics to be calculated periodically
    """

    active_users_enabled = Bool(
        True,
        help="""
        Enable active_users prometheus metric.

        Populates a `jupyterhub_active_users` prometheus metric, with a label `period` that counts the time period
        over which these many users were active. Periods are 24h (24 hours), 7d (7 days) and 30d (30 days).
        """,
        config=True,
    )

    active_users_update_interval = Integer(
        60 * 60,
        help="""
        Number of seconds between updating active_users metrics.

        To avoid extra load on the database, this is only calculated periodically rather than
        at per-minute intervals. Defaults to once an hour.
        """,
        config=True,
    )

    db = Any(help="SQLAlchemy db session to use for performing queries")

    def update_active_users(self):
        """Update active users metrics."""

        # All the metrics should be based off a cutoff from a *fixed* point, so we calculate
        # the fixed point here - and then calculate the individual cutoffs in relation to this
        # fixed point.
        now = utcnow()
        cutoffs = {
            ActiveUserPeriods.twenty_four_hours: now - timedelta(hours=24),
            ActiveUserPeriods.seven_days: now - timedelta(days=7),
            ActiveUserPeriods.thirty_days: now - timedelta(days=30),
        }
        for period, cutoff in cutoffs.items():
            value = (
                self.db.query(orm.User).filter(orm.User.last_activity >= cutoff).count()
            )

            self.log.info(f'Found {value} active users in the last {period}')
            ACTIVE_USERS.labels(period=period.value).set(value)

    def start(self):
        """
        Start the periodic update process
        """
        if self.active_users_enabled:
            # Setup periodic refresh of the metric
            pc = PeriodicCallback(
                self.update_active_users,
                self.active_users_update_interval * 1000,
                jitter=0.01,
            )
            pc.start()

            # Update the metrics once on startup too
            self.update_active_users()
