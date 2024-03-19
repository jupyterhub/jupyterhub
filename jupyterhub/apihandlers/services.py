"""Service handlers

Currently GET-only, no actions can be taken to modify services.
"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
from typing import Optional, Tuple

from tornado import web

from .. import orm
from ..roles import get_default_roles
from ..scopes import Scope, _check_token_scopes, needs_scope
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
        if service_name not in self.services:
            raise web.HTTPError(404, f"No such service: {service_name}")
        service = self.services[service_name]
        self.write(json.dumps(self.service_model(service)))

    def _check_service_scopes(self, spec: dict):
        user = self.current_user
        requested_scopes = []
        if spec.get('admin'):
            default_roles = get_default_roles()
            admin_scopes = [
                role['scopes'] for role in default_roles if role['name'] == 'admin'
            ]
            requested_scopes.extend(admin_scopes[0])

        requested_client_scope = spec.get('oauth_client_allowed_scopes')
        if requested_client_scope is not None:
            requested_scopes.extend(requested_client_scope)
        if len(requested_scopes) > 0:
            try:
                _check_token_scopes(requested_scopes, user, None)
            except ValueError as e:
                raise web.HTTPError(400, str(e))

    async def add_service(self, spec: dict) -> Service:
        """Add a new service and related objects to the database

        Args:
            spec (dict): The service specification

        Raises:
            web.HTTPError: Raise if the service is not created

        Returns:
            Service: Returns the service instance.

        """

        self._check_service_model(spec)
        self._check_service_scopes(spec)

        service_name = spec["name"]
        managed = bool(spec.get('command'))
        if managed:
            msg = f"Can not create managed service {service_name} at runtime"
            self.log.error(msg, exc_info=True)
            raise web.HTTPError(400, msg)
        try:
            new_service = self.service_from_spec(spec)
        except Exception:
            msg = f"Failed to create service {service_name}"
            self.log.error(msg, exc_info=True)
            raise web.HTTPError(400, msg)

        if new_service is None:
            raise web.HTTPError(400, f"Failed to create service {service_name}")

        if new_service.api_token:
            # Add api token to database
            await self.app._add_tokens(
                {new_service.api_token: new_service.name}, kind='service'
            )
        if new_service.url:
            # Start polling for external service
            service_status = await self.app.start_service(service_name, new_service)
            if not service_status:
                self.log.error(
                    'Failed to start service %s',
                    service_name,
                    exc_info=True,
                )

        if new_service.oauth_no_confirm:
            oauth_no_confirm_list = self.settings.get('oauth_no_confirm_list')
            msg = f"Allowing service {new_service.name} to complete OAuth without confirmation on an authorization web page"
            self.log.warning(msg)
            oauth_no_confirm_list.add(new_service.oauth_client_id)

        return new_service

    @needs_scope('admin:services')
    async def post(self, service_name: str):
        data = self.get_json_body()
        service, _ = self.find_service(service_name)

        if service is not None:
            raise web.HTTPError(409, f"Service {service_name} already exists")

        if not data or not isinstance(data, dict):
            raise web.HTTPError(400, "Invalid service data")

        data['name'] = service_name
        new_service = await self.add_service(data)
        self.write(json.dumps(self.service_model(new_service)))
        self.set_status(201)

    @needs_scope('admin:services')
    async def delete(self, service_name: str):
        service, orm_service = self.find_service(service_name)

        if service is None:
            raise web.HTTPError(404, f"Service {service_name} does not exist")

        if service.from_config:
            raise web.HTTPError(
                405, f"Service {service_name} is not modifiable at runtime"
            )
        try:
            await self.remove_service(service, orm_service)
            self.services.pop(service_name)
        except Exception:
            msg = f"Failed to remove service {service_name}"
            self.log.error(msg, exc_info=True)
            raise web.HTTPError(400, msg)

        self.set_status(200)

    async def remove_service(self, service: Service, orm_service: orm.Service) -> None:
        """Remove a service and all related objects from the database.

        Args:
            service (Service): the service object to be removed

            orm_service (orm.Service): The `orm.Service` object linked
            with `service`
        """
        if service.managed:
            await service.stop()

        if service.oauth_client:
            self.oauth_provider.remove_client(service.oauth_client_id)

        if orm_service._server_id is not None:
            orm_server = (
                self.db.query(orm.Server).filter_by(id=orm_service._server_id).first()
            )
            if orm_server is not None:
                self.db.delete(orm_server)

        if service.oauth_no_confirm:
            oauth_no_confirm_list = self.settings.get('oauth_no_confirm_list')
            oauth_no_confirm_list.discard(service.oauth_client_id)

        self.db.delete(orm_service)
        self.db.commit()

    def service_from_spec(self, spec) -> Optional[Service]:
        """Create service from api request"""
        service = self.app.service_from_spec(spec, from_config=False)
        self.db.commit()
        return service

    def find_service(
        self, name: str
    ) -> Tuple[Optional[Service], Optional[orm.Service]]:
        """Get a service by name
        return None if no such service
        """
        orm_service = orm.Service.find(db=self.db, name=name)
        if orm_service is not None:
            service = self.services.get(name)
            return service, orm_service

        return (None, None)


default_handlers = [
    (r"/api/services", ServiceListAPIHandler),
    (r"/api/services/([^/]+)", ServiceAPIHandler),
]
