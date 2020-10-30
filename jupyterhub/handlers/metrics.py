from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import generate_latest
from prometheus_client import REGISTRY

from ..utils import metrics_authentication
from .base import BaseHandler


class MetricsHandler(BaseHandler):
    """
    Handler to serve Prometheus metrics
    """

    @metrics_authentication
    async def get(self):
        self.set_header('Content-Type', CONTENT_TYPE_LATEST)
        self.write(generate_latest(REGISTRY))


default_handlers = [(r'/metrics$', MetricsHandler)]
