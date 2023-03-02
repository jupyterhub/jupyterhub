"""Service handlers

Currently GET-only, no actions can be taken to modify services.
"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
from typing import Optional

from tornado import web

from .. import orm
from ..scopes import Scope, needs_scope
from ..services.service import Service
from .base import APIHandler


class ServiceListAPIHandler(APIHandler):
    @needs_scope('list:services')
    def get(self):
        data = {}
        service_scope = self.parsed_scopes['list:services']
        for name, service in self.services.items():
            if service_scope == Scope.ALL or name in service_scope.get("service", {}):
                model = self.service_model(service)
                data[name] = model
        self.write(json.dumps(data))


class ServiceAPIHandler(APIHandler):
    @needs_scope('read:services', 'read:services:name', 'read:roles:services')
    def get(self, service_name):
        service = self.services[service_name]
        self.write(json.dumps(self.service_model(service)))

    @needs_scope('admin:services')
    async def post(self, service_name: str):
        data = self.get_json_body()
        service = self.find_service(service_name)

        if service is not None:
            raise web.HTTPError(409, f"Service {service_name} already exists")

        if not data or not isinstance(data, dict):
            raise web.HTTPError(400, "Invalid service data")

        data['name'] = service_name
        self._check_service_model(data)
        new_service = self.service_from_spec(data)

        if new_service is None:
            raise web.HTTPError(400, f'Failed to create service {service_name}')
        if new_service.api_token:
            # Add api token to database
            await self.app._add_tokens(
                {new_service.api_token: new_service.name}, kind='service'
            )
        elif new_service.managed:
            new_service.api_token = new_service.orm.new_api_token(
                note='generated at runtime'
            )

        self.write(json.dumps(self.service_model(new_service)))
        self.set_status(201)

    @needs_scope('admin:services')
    async def delete(self, service_name: str):
        service = self.find_service(service_name)

        if service is None:
            raise web.HTTPError(404, f"Service {service_name} does not exists")

        if service.from_config:
            raise web.HTTPError(
                405, f"Service {service_name} is not modifiable at runtime"
            )

        if service.managed:
            await service.stop()

        if service.oauth_client:
            self.oauth_provider.remove_client(service.oauth_client_id)

        orm_service = orm.Service.find(db=self.db, name=service_name)
        if orm_service is not None:
            if service.api_token is not None:
                # Remove api token from database
                orm_token = (
                    self.db.query(orm.APIToken)
                    .filter_by(service_id=orm_service.id)
                    .first()
                )
                if orm_token is not None:
                    self.db.delete(orm_token)

            self.services.pop(service_name)
            self.db.delete(orm_service)

        self.db.commit()
        self.set_status(200)

    def service_from_spec(self, spec) -> Optional[Service]:
        """Create service from api request"""
        service = self.app._service_from_spec(spec, from_config=False)
        self.db.commit()
        return service

    def find_service(self, name: str) -> Optional[Service]:
        """Get a service by name
        return None if no such service
        """
        orm_service = orm.Service.find(db=self.db, name=name)
        if orm_service is not None:
            service = self.services.get(name)
            return service


default_handlers = [
    (r"/api/services", ServiceListAPIHandler),
    (r"/api/services/([^/]+)", ServiceAPIHandler),
]
