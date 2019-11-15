.. _api-index:

##############
JupyterHub API
##############

:Release: |release|
:Date: |today|

JupyterHub also provides a REST API for administration of the Hub and users.
The documentation on `Using JupyterHub's REST API <../reference/rest.html>`_ provides
information on:

- what you can do with the API
- creating an API token
- adding API tokens to the config files
- making an API request programmatically using the requests library
- learning more about JupyterHub's API

The same JupyterHub API spec, as found here, is available in an interactive form
`here (on swagger's petstore) <http://petstore.swagger.io/?url=https://raw.githubusercontent.com/jupyterhub/jupyterhub/master/docs/rest-api.yml#!/default>`__.
The `OpenAPI Initiative`_ (fka Swagger™) is a project used to describe
and document RESTful APIs.

JupyterHub API Reference:

.. toctree::

    app
    auth
    spawner
    proxy
    user
    service
    services.auth


.. _OpenAPI Initiative: https://www.openapis.org/
