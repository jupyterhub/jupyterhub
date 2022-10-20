(api-only)=

# Deploying JupyterHub In "API Only Mode"

Jupyterhub, as a service for deploying and managing Jupyter servers for users, exposes its functionality, _primarily_ through a [REST API](rest).

For convenience, Jupyterhub also ships a basic web UI, built on the REST API. The basic web UI enables users to easily interact with their servers. E.g by clicking on the button to quickly start or stop their servers. It also enable admins to perform basic user and server mananagement tasks.

## The REST API

Previously, one could only achieve some admin UI functionalities through admin pages, such as paginated requests. The REST API provides additional functionality beyond what is available in the basic web UI. With Jupyterhub 2.0, the UI will always be composed from the REST API. This means that information on the pages will not be reliable, unless made available through the API.

## Why Rest API Only?

### Limited UI customization via templates

The JupyterHub UI can be customized through extensive HTML [templates](templates), but the scope at which it can be customized, is limited. It supports adding of content and messages to existing pages, but the page flow and available pages, cannot be customized.

### Rich UI Customization with REST API based Apps

JupyterHub is primarily used as an API for managing Jupyter servers for other Jupyter-based applicatons that might want to present a different User Experience. However, With an option of a fully customized experience available, you can now disable the hub UI and easily use your own pages, together with the JupyterHub Rest API, to build your own web applications to serve your users; relying on the hub only as an API for managing Users and Servers.

An Example of such application is the BinderHub, which powers https://mybinder.org, and motivates many of these changes.

BinderHub is distinct from a traditional JupyterHub deployment because it uses temporary users created for each launch.

Instead of presenting a login page, users are presented with a form to specify what environment they would like to launch:

![Binder launch form](../images/binderhub-form.png)


**When a launch is requested:**

1. An image is built, if necessary.
2. A temporary user is created.
3. A server is launched for that user, and
4. When running, users are redirected to an already running server with an auth token in the URL.
5. After the session is over, the user is deleted.

**This means that a lot of JupyterHub's UI flow doesn't make sense:**

- There is no way for users to login.
- The human user doesn't map onto a JupyterHub `User` in a meaningful way.
- When a server isn't running, there isn't a 'restart your server' action available because the user has been deleted.
- Users do not have any access to any Hub functionality, so presenting pages for those features would be confusing.

BinderHub is one of the motivating use cases for JupyterHub supporting being used _only_ via its API.
We'll use BinderHub here as an example of various configuration options.

[binderhub]: https://binderhub.readthedocs.io

## Disabling Hub UI

`c.JupyterHub.hub_routespec` is a configuration option to specify which URL prefix should be routed to the Hub.
The default is `/` which means that the Hub will receive all requests not already specified to be routed somewhere else.

There are three values that are most logical for `hub_routespec`:

- `/` - This is the default, and used in most deployments. It is also the only option prior to JupyterHub 1.4.
- `/hub/` - This serves only Hub pages, both UI and API
- `/hub/api` - This serves _only the Hub API_, so all Hub UI is disabled. Aside from the OAuth confirmation page, if used.

If you choose a hub routespec other than `/`, the main JupyterHub feature you will lose is the automatic handling of requests for `/user/:username` when the requested server is not running.

JupyterHub's handling of this request shows this page, telling you that the server is not running, with a button to launch it again:

![screenshot of hub page for server not running](../images/server-not-running.png)

If you set `hub_routespec` to something other than `/`, it is likely that you also want to register another destination for `/` to handle requests to not-running servers.

If you don't, you will see a default 404 page from the proxy:

![screenshot of CHP default 404](../images/chp-404.png)

For mybinder.org, the default "start my server" page doesn't make sense,
because when a server is gone, there is no restart action. Instead, we provide hints about how to get back to a link to start a _new_ server:

![screenshot of mybinder.org 404](../images/binder-404.png)

To achieve this, mybinder.org registers a route for `/` that goes to a custom endpoint that runs nginx and only serves this static HTML error page.

This is set with

```python
c.Proxy.extra_routes = {
    "/": "http://custom-404-entpoint/",
}
```

You may want to use an alternate behavior, such as redirecting to a landing page, or taking some other action based on the requested page.

If you use `c.JupyterHub.hub_routespec = "/hub/"`, then all the Hub pages will be available, and only this default-page-404 issue will come up.

If you use `c.JupyterHub.hub_routespec = "/hub/api/"`, then only the Hub _API_ will be available, and all UI will be up to you.

mybinder.org takes this last option, because none of the Hub UI pages really make sense.
Binder users don't have any reason to know or care that JupyterHub happens to be an implementation detail of how their environment is managed. Seeing Hub error pages and messages in that situation is more likely to be confusing than helpful.

:::{versionadded} 1.4

`c.JupyterHub.hub_routespec` and `c.Proxy.extra_routes` are new in JupyterHub 1.4.
:::
