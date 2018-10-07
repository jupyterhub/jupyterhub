from prometheus_client import REGISTRY, CONTENT_TYPE_LATEST, generate_latest
from tornado import gen

from .base import BaseHandler
from ..utils import metrics_authentication

class MetricsHandler(BaseHandler):
    """
    Handler to serve Prometheus metrics
    """
    @metrics_authentication
    async def get(self):
        self.set_header('Content-Type', CONTENT_TYPE_LATEST)
        self.write(generate_latest(REGISTRY))

default_handlers = [
    (r'/metrics$', MetricsHandler)
]
