"""Proxy handlers"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json

from tornado import web

from ..scopes import needs_scope
from .base import APIHandler


class ProxyAPIHandler(APIHandler):
    @needs_scope('proxy')
    async def get(self):
        """GET /api/proxy fetches the routing table

        This is the same as fetching the routing table directly from the proxy,
        but without clients needing to maintain separate
        """
        offset, limit = self.get_api_pagination()

        all_routes = await self.proxy.get_all_routes()

        if offset == 0 and len(all_routes) < limit:
            routes = all_routes
        else:
            routes = {}
            end = offset + limit
            for i, key in enumerate(sorted(all_routes.keys())):
                if i < offset:
                    continue
                elif i >= end:
                    break
                routes[key] = all_routes[key]

        if self.accepts_pagination:
            data = self.paginated_model(routes, offset, limit, len(all_routes))
        else:
            data = routes

        self.write(json.dumps(data))

    @needs_scope('proxy')
    async def post(self):
        """POST checks the proxy to ensure that it's up to date.

        Can be used to jumpstart a newly launched proxy
        without waiting for the check_routes interval.
        """
        await self.proxy.check_routes(self.users, self.services)

    @needs_scope('proxy')
    async def patch(self):
        """PATCH updates the location of the proxy

        Can be used to notify the Hub that a new proxy is in charge
        """
        if not self.request.body:
            raise web.HTTPError(400, "need JSON body")

        try:
            model = json.loads(self.request.body.decode('utf8', 'replace'))
        except ValueError:
            raise web.HTTPError(400, "Request body must be JSON dict")
        if not isinstance(model, dict):
            raise web.HTTPError(400, "Request body must be JSON dict")

        if 'api_url' in model:
            self.proxy.api_url = model['api_url']
        if 'auth_token' in model:
            self.proxy.auth_token = model['auth_token']
        self.log.info("Updated proxy at %s", self.proxy)
        await self.proxy.check_routes(self.users, self.services)


default_handlers = [(r"/api/proxy", ProxyAPIHandler)]
