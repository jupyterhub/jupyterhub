## What is Dockerfile.alpine
Dockerfile.alpine  contains base image for jupyterhub. It does not work independently, but only as part of a full jupyterhub cluster

## How to use it?

1. A running configurable-http-proxy, whose API is accessible. 
2. A jupyterhub_config file.
3. Authentication and other libraries required by the specific jupyterhub_config file.


## Steps to test it outside a cluster

* start configurable-http-proxy in another container
* specify CONFIGPROXY_AUTH_TOKEN env in both containers
* put both containers on the same network (e.g. docker network create jupyterhub; docker run ... --net jupyterhub)
* tell jupyterhub where CHP is (e.g. c.ConfigurableHTTPProxy.api_url = 'http://chp:8001')
* tell jupyterhub not to start the proxy itself (c.ConfigurableHTTPProxy.should_start = False)
* Use dummy authenticator for ease of testing. Update following in jupyterhub_config file
    - c.JupyterHub.authenticator_class = 'dummyauthenticator.DummyAuthenticator'
    - c.DummyAuthenticator.password = "your strong password"
