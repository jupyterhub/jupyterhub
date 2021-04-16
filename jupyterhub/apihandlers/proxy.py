"""Proxy handlers"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json

from tornado import web

from ..utils import admin_only
from .base import APIHandler


class ProxyAPIHandler(APIHandler):
    @admin_only
    async def get(self):
        """GET /api/proxy fetches the routing table

        This is the same as fetching the routing table directly from the proxy,
        but without clients needing to maintain separate
        """
        offset = self.get_argument("offset", None)
        limit = self.get_argument("limit", self.settings['app'].api_page_default_limit)
        max_limit = self.settings['app'].api_page_max_limit

        routes = await self.proxy.get_all_routes()

        if offset is not None:
            try:
                offset = int(offset)
            except Exception as e:
                raise web.HTTPError(
                    400, "Invalid argument type, offset must be an integer"
                )
            routes = {
                key: routes[key]
                for key in list(routes.keys())[offset:]
                if key in routes
            }

        if limit != self.settings['app'].api_page_default_limit:
            try:
                limit = int(limit)
                if limit > max_limit:
                    limit = max_limit
            except Exception as e:
                raise web.HTTPError(
                    400, "Invalid argument type, limit must be an integer"
                )
        routes = {
            key: routes[key] for key in list(routes.keys())[:limit] if key in routes
        }

        self.write(json.dumps(routes))

    @admin_only
    async def post(self):
        """POST checks the proxy to ensure that it's up to date.

        Can be used to jumpstart a newly launched proxy
        without waiting for the check_routes interval.
        """
        await self.proxy.check_routes(self.users, self.services)

    @admin_only
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
