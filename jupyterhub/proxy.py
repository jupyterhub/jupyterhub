from traitlets.config import LoggingConfigurable


class Proxy(LoggingConfigurable):
    """
    Base class for configurable proxies that JupyterHub can use
    """
    def add_route(self, routespec, target, data):
        """
        Add a route to the proxy

        :param urlspec: A specification for which this route will be matched.
         Could be either a url_prefix or a fqdn.
        :param target: A URL that will be the target of this route.
        :param data: A JSONable dict that will be associated with this route, and will
         be returned when retrieving information about this route.

        Will raise an appropriate exception (FIXME: find what?) if the route could
        not be added.

        The proxy implementation should also have a way to associate the fact that a
        route came from JupyterHub.
        """
        pass

    def fetch_all_routes(self):
        """
        Fetch and return all the routes associated by JupyterHub from the proxy

        Should return a list of dictionaries, where each dictionary has the same
        structure as the return value of `get_route`
        """
        pass

    def get_route(self, routespec):
        """
        Return the route info for a given routespec

        :param routespec: The route specification that was used to add this routespec

        Returns a dict with the following info:
        routespec: The normalized route specification passed in to add_route
        target: The target for this route
        data: The arbitrary data that was passed in by JupyterHub when adding this
        route.

        Returns `None` if there are no routes matching the given routespec
        """
        pass

    def delete_route(self, routespec):
        """
        Delete a route with a given routespec if it exists.
        """
        pass
