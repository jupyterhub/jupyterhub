# JupyterHub services

JupyterHub 0.7 adds the notion of Services.
A Service is a process that interacts with the Hub REST API.
Services may perform actions such as shutting down user servers that have been idle for some time,
or registering additional web servers that should also use the Hub's authentication
and be served behind the Hub's proxy.

There are two main characteristics of services:

1. Is it **managed** by JupyterHub?
2. Does it have a web server that should be added to the proxy?

If a `command` is specified for launching the service, it will be started and managed by the Hub.
If a `url` is specified for where the service runs its own webserver,
it will be added to the Hub's proxy at `/service/:service-name`.

## Managed services

**Managed** services are services that the Hub starts and is responsible for.
These can only be local subprocesses of the Hub,
and the Hub will take care of starting these processes and restarting them if they stop.

While there are similarities with notebook Spawners,
there are no plans to support the same spawning abstractions as notebook.
If you want to run these services in docker or other environments,
you can register it as an external service below.

A managed service is characterized by the `command` specified for launching the service.


```python
c.JupyterHub.services = [
    {
        'name': 'cull-idle',
        'admin': True,
        'command': ['python', '/path/to/cull-idle.py', '--interval']
    }
]
```

In addition to `command`, managed services can take additional optional parameters,
to describe the environment in which to start the process:

- `env: dict` additional environment variables for the service.
- `user: str` name of the user to run the server as if different from the Hub.
    Requires Hub to be root.
- `cwd: path` directory in which to run the service, if different from the Hub directory.

When the service starts, the Hub will pass the following environment variables:

```
JUPYTERHUB_SERVICE_NAME: the name of the service ('cull-idle' above)
JUPYTERHUB_API_TOKEN: API token assigned to the service
JUPYTERHUB_API_URL: URL for the JupyterHub API (http://127.0.0.1:8080/hub/api)
JUPYTERHUB_BASE_URL: Base URL of the Hub (https://mydomain[:port]/)
JUPYTERHUB_SERVICE_PREFIX: URL path prefix of this service (/services/cull-idle/)
```

## External services

You can use your own service management tools, such as docker or systemd, to manage JupyterHub services.
These are not subprocesses of the Hub, and you must tell JupyterHub what API token the service is using to perform its API requests.
Each service will need a unique API token because the Hub authenticates each API request,
identifying the originating service or user.

An example of an externally managed service with admin access and running its own web server:

```python
c.JupyterHub.services = [
    {
        'name': 'my-web-service',
        'url': 'https://10.0.1.1:1984',
        'api_token': 'super-secret',
    }
]
```


## Writing your own services

TODO

### Authenticating with the Hub

TODO

JupyterHub 0.7 introduces some utiltiies for you to use that allow you to use the Hub's authentication mechanism.