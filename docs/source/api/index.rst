.. _api-index:

####################
 The JupyterHub API
####################

:Release: |release|
:Date: |today|

JupyterHub also provides a REST API for administration of the Hub and users.
The documentation on `Using JupyterHub's REST API <../rest.html>`_ provides
information on:

- Creating an API token
- Adding tokens to the configuration file (optional)
- Making an API request

The same JupyterHub API spec, as found here, is available in an interactive form
`here (on swagger's petstore) <http://petstore.swagger.io/?url=https://raw.githubusercontent.com/jupyterhub/jupyterhub/master/docs/rest-api.yml#!/default>`__.
The `OpenAPI Initiative`_ (fka Swagger™) is a project used to describe
and document RESTful APIs.

JupyterHub API Reference:

.. toctree::

    auth
    spawner
    user
    services.auth


.. _OpenAPI Initiative: https://www.openapis.org/
