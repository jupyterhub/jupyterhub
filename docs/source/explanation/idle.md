(idle)=

# JupyterHub and idleness

```{seealso}
This doc assumes some familiarity with [](#explanation:concepts), check it out before getting too deep into this.
```

JupyterHub tracks a `last_activity` field on users and servers whenever it notices "activity".
This field is represented as an ISO8601 timestamp in the JupyterHub API, indicating the last time there was "activity" by that user or on that server.
These can be simply informative metrics (they show up in the admin UI and REST API), but are also meant to inform a measure of "idleness" which can be used to make decisions like shutting down servers that haven't been used in some time, to avoid deployments paying for unused resources.

But this raises the question:

> What is activity?

The answer can be complex.
We want to answer a few questions.

For admins:

- How can I shut down idle servers?
- How can I influence what counts as an idle server?
- Why is this server that I'm pretty sure is idle not getting shut down?

For users:

- How can I ensure my server _doesn't_ get shut down, especially if I'm doing something that doesn't look like typical interactive work?
- How can I ensure my server _does_ shut down to avoid accruing compute-hours against my quota or incurring compute costs?

A few keywords that we will use throughout:

active
: has had some "activity" over a period of time (deployment-defined)

idle/inactive
: not active (a server is always either active or idle/inactive)

cull
: shut down a server (or kernel or other resource) that has become idle

```{note}
This document has a lot of detail of how things work.
If you got here with a question already, you might want to start at [](#idle-troubleshooting).
```

(flavors-of-idleness)=

## Three flavors of idleness

There are generally three situations in which a server is 'idle' (i.e. a human isn't actively using it), and the characteristics and configurations relevant to making sure it is considered idle (or not) vary in each:

1. Fully disconnected (no browsers connected to the server)
2. A browser tab is left open, but forgotten in the background (_shouldn't_, but can, maintain ongoing network activity)
3. A browser tab is open _and is focused_ (often _is_ considered a good proxy for human attention, but deployments can disagree)

The first case will usually be considered idle by the typical monitoring mechanisms.
The last will usually be considered active, unless some significant effort is made.
The second case (a tab open, but no human is looking at it) is the one most often misattributed as active that deployments would _like_ to be considered idle and culled.

## Sources of activity

JupyterHub tracks activity on the user and server level, while Jupyter Server tracks activity.
Activity can come from API requests, network traffic through the proxy, or tracked events internal to each user's server.
This section covers each source in detail.

### User activity

On the User, any authenticated request as that user counts as activity,
so visiting JupyterHub pages, making API requests, visiting your own server or any JupyterHub-authenticated service.
All of these count towards your user's activity.
A user's last activity is useful in reporting (such as monthly active users),
but action is rarely taken as a result of an inactive user.
More often actionable, on the other hand, is activity on a user's _server_,
where evidence of inactivity is often used to shut the server down to avoid wasting resources.
At the same time, server activity is more complicated to define,
and is aggregated from a number of different sources.

### Network traffic

The first source of activity on a server is the proxy.
The default proxy (configurable-http-proxy) tracks _any_ network activity to a server.
That's any network request, any websocket message, etc. _through the proxy_ (i.e. not internal requests between JupyterHub components).

Tracking network traffic activity is a feature of configurable-http-proxy (JupyterHub's default, used by the [jupyterhub helm chart](https://github.com/jupyterhub/zero-to-jupyterhub-k8s)), and not shared by the [Traefik proxy implementation](https://jupyterhub-traefik-proxy.readthedocs.io/), which is used by [The Littlest JupyterHub](https://tljh.jupyter.org/).

Using any network traffic as activity is a blunt instrument, but it is also one that is clearly defined and reliable: if any client is talking to your server, there's a good chance it is being used.

_However_.

In a lot of cases, an application like JupyterLab or RStudio makes polling requests that mean there's always traffic if it's open, even if there's no human there doing anything.
That means leaving a tab open is often enough to keep a server active,
much to the frustration of their JupyterHub admins and those paying for hosting.

```{note}
JupyterLab is designed to disable polling when the tab is not _focused_ (i.e. you are not looking at it), specifically to avoid a long-forgotten tab making continuous requests to the server.
However, not all JupyterLab _Extensions_ follow this behavior.
If you see JupyterLab or an Extension consistently polling requests in logs while it not focused, please report it as a bug to the package making the requests.
```

### Configuring network traffic activity

JupyterHub polls the proxy for activity every `JupyterHub.last_activity_interval` seconds (default: 300).
That makes it the effective _resolution_ of JupyterHub's activity tracking.
You shouldn't enable culling with a timeout any shorter than twice the `last_activity_interval`, or you might end up culling active users.

Setting this interval to 0:

```python
c.JupyterHub.last_activity_interval = 0
```

disables retrieving activity information from the proxy, relying on other activity sources.
Doing so gives your deployment more precise control over what counts as activity,
but you must make sure that relevant user activity does get tracked and reported somewhere.
The main benefit of disabling tracking activity in the proxy is that idle traffic to a server is less likely to keep it alive.
Proxy activity tracking is a blunt instrument, but it is at least simple and well defined.

## Activity in the server

Jupyter Server tracks activity itself, and because Jupyter Server knows what each request _means_, it can make more fine-grained decisions about what counts as activity and when to shut things down.
It can also track internal state when there are no requests happening, to enable a server to identify itself as "active"
without interactions.

In summary, the Jupyter Server will report activity on any API, kernel, or terminal to JupyterHub.
It _can_ shut itself down if it considers itself inactive, but this is disabled by default and will not occur if there is any "activity", including if any kernels or terminals are running, even if they are idle.

Jupyter Server tracks _multiple_ sources of activity, and reports them to JupyterHub every [`$JUPYTERHUB_ACTIVITY_INTERVAL`](#JupyterHubSingleUser.hub_activity_interval) seconds (default: 300).
Like with network activity, make sure to set your last activity reporting interval to be short enough relative to your culling interval and timeout.

Like JupyterHub, authenticated API requests to the server count as activity.
But there are other kinds of activity, such as kernel activity and execution state,
terminal activity, and extension activity, which can be considered.

Jupyter Server Extensions have the ability to track activity and report it to Jupyter Server.
The Server tracks a global `settings` dictionary, available to all extensions.
Any timestamp stored in the global `settings` dict that ends with `_last_activity` will be considered.
When the Server is reporting activity to the Hub, it looks at all of these timestamps and uses the latest one as the last activity on theServer.

Extensions also have a `current_activity` indicator which is a boolean that _doesn't_ update the `last_activity` timestamp,
but informs Jupyter Server's own "shutdown if there's no activity" behavior.

API requests to a Jupyter Server can be made with `?no_track_activity=1` to prevent updating `last_activity`.
This is useful if you have a tool or service that might poll the server for something and don't want it to be treated as keeping it active.

### Kernel activity

Just like JupyterHub manages servers and can cull them based on inactivity,
Jupyter Server manages _kernels_ and can cull _them_ based on inactivity.

Kernels have 3 kinds of activity to consider:

- kernel message events
- is the kernel "busy" processing a message?
- are any clients currently connected to the kernel (i.e. is a notebook open)?

Sources of kernel activity:

- every message on the kernels IOPub channel
- starting or restarting a kernel
- interrupts of the kernel

### Configuring kernel activity

Jupyter Server's [MappingKernelManager](inv:jupyter-server#*.MappingKernelManager) defines some options for configuring how kernels are considered "idle" and available for culling.

The defaults are conservative (in fact, the default is to entirely disable culling), because prematurely culling user kernels can result in lost work.
A kernel is only considered idle if none of the following are true:

1. there has been activity in the last `cull_idle_timeout` seconds
2. the kernel is busy (processing a request such as a cell execution)
3. any client is connected to the kernel

You can tune these to suit your needs via options on `MappingKernelManager` in your `jupyter_server_config` in the user environment (i.e. _not_ JupyterHub configuration).

- [cull_idle_timeout](inv:jupyter-server:py#*.MappingKernelManager.cull_idle_timeout) specifies the timeout (in seconds) at which to consider a kernel idle. If left unset, culling of kernels is entirely disabled.
- [cull_interval](inv:jupyter-server:py#*.MappingKernelManager.cull_interval) specifies the interval (in seconds) on which to check for idle kernels to cull
- [cull_connected](inv:jupyter-server:py#*.MappingKernelManager.cull_connected) specifies whether idle kernels with active connections should be considered for culling
- [cull_busy](inv:jupyter-server:py#*.MappingKernelManager.cull_busy) specifies whether a kernel in the middle of processing a request will be considered for culling
- [untracked_message_types](inv:jupyter-server:py#*.MappingKernelManager.untracked_message_types) specifies which messages to consider activity.
  By default, whenever a kernel processes a message from the client (such as an execution or introspection),
  it will be treated as activity.

Busy and connected kernels, if they are not producing message events, do _not_ contribute to the overall `last_activity`.
Those signals are only taken into account by the server's internal kernel culler.

Tips for more aggressive culling:

1. set `cull_connected = True` if you want to prevent a left-open JupyterLab tab from keeping a kernel alive
2. set `cull_busy = True` if you want to prevent a forgotten infinite loop from keeping a kernel alive

```{warning}
Note that these aggressive choices are not the default for a reason - culling connected kernels may mean culling kernels that folks aren't executing with because they are reading or thinking.
Culling busy kernels means you are explicitly stopping users' requested executions.
```

### Terminal tracking

Jupyter Server Terminals also track activity like kernels, and have analogous configuration, also disabled by default:

```python
c.TerminalManager.cull_inactive_timeout = 600 # timeout to cull terminals with no activity
c.TerminalManager.cull_interval = 60 # interval to check for idle terminals
```

### Proxied server applications

If you proxy other applications (e.g. RStudio) via [jupyter-server-proxy](inv:jupyter-server-proxy#index),
we reintroduce the issue of a proxy needing to track activity to a proxied service without the knowledge of whether each request is truly meaningful.
Like configurable-http-proxy, jupyter-server-proxy tracks every request to a proxied application as "activity".
You can exclude a given proxied application from being considered activity by specifying `update_last_activity: False`:

```python
c.ServerProxy.servers = {
    "doesntcount": {
        "command": ["..."],
        "update_last_activity": False,
    }
}
```

Starting with jupyter-server-proxy 4.6, you can further control _which_ proxied requests count as activity,
by specifying [`exclude_last_activity_patterns`](inv:jupyter-server-proxy:std:doc#server-process) as a list of URL patterns (regular expressions) to exclude from contributing to the `last_activity` metric:

```python
c.ServerProxy.servers = {
    "pollstoomuch": {
        "command": ["..."],
        "exclude_last_activity_patterns": [
          ".*/busy-poller$",
        ],
    }
}
```

`jupyter-rsession-proxy` 2.6 uses this to try to avoid the requests typical of an idle RStudio connection being treated as user activity.

## Other servers

If you use a single-user server implementation other than the default `jupyterhub-singleuser`,
JupyterHub doesn't govern how they track activity, or even if they do at all.
It is up to the application to report activity or not.
Make sure you check the server's activity tracking behavior before disabling activity tracking in the proxy.

Servers (or any service with `users:activity` scope) can make requests [POST /hub/api/users/:name/activity](rest-api-post-user-activity) to register activity for a server,
and are free to define whatever mechanisms they choose.

## Two kinds of culling

'Culling' is what we call shutting down a server or kernel once it is considered to be idle.
This typically happens in one of two ways.

### JupyterHub idle culler

[jupyterhub-idle-culler](https://github.com/jupyterhub/jupyterhub-idle-culler) is an example of a service for shutting down servers that have become idle, used in most JupyterHub deployments.
It has lots of configuration of its own, but the key points are:

1. a timeout for culling idle servers
2. a max age for culling servers that have been running a long time, even if they appear to be idle
3. more detailed controls over precisely which users and servers to cull and when
4. the only piece of information to _directly_ consider for idleness is the `last_activity` metric on the server in JupyterHub
5. the JupyterHub REST API is used to retrieve activity and shutdown servers

`jupyterhub-idle-culler` checks the `last_activity` timestamp of the server and compares it to these configuration options.
We've seen that this single per-server timestamp is a coarse summary of all the information available,
and can lead to servers that a human would reasonably describe as being idle not being culled.
This leads us to Jupyter Server's _internal_ culling.

### Jupyter Server internal culler

Jupyter Server's internal culling is enabled by setting

```python
ServerApp.shutdown_no_activity_timeout = 1800  # seconds
```

to a timeout (in seconds) in the single-user environment (`jupyter_server_config.py`).

In combination with Kernel and other activity tracking,
when there are no terminals and no kernels running (e.g. culled by above configuration),
and no API requests or other Extension activity registered within this timeout,
the server will shut itself down.

(idle-troubleshooting)=

## Troubleshooting

Troubleshooting idleness usually means that you and JupyterHub disagree about whether a server is idle.
Either, you consider it idle and it's getting activity registered,
or you consider it active, but it is getting culled when you don't want it to.

It is useful to first identify which [flavor of idleness](flavors-of-idleness) your server is in when the disagreement occurs, because it affects the tools available to you to address the difference.

### Why is this idle server _not_ getting culled?

The most common issue is a server that you think should be idle and a candidate for culling is staying 'active'.
The main thing to check here is what is the source of 'activity'.
The useful logs for this are:

- the server's logs, look for any requests that are happening when a server is known to be 'idle'
- the proxy's logs. This usually requires enabling debug logging, because the proxy does not log every request
- the hub's logs, especially for `200 POST /hub/api/users/USERNAME/activity`

Debug logging may be necessary to get a full picture.
Once you've identified what requests are triggering the activity, you can start the process of trying to either prevent those requests, or prevent those requests from counting toward activity.

### How do I enable _only_ internal activity?

As discussed above, you may want to try to disable the proxy's activity tracking and rely only on Jupyter Server's internal activity tracking.

To disable proxy activity tracking, add to your JupyterHub config:

```python
c.JupyterHub.last_activity_interval = 0
```

Then the only source of activity will be the requests to `/hub/api/users/.../activity` coming from user servers.

### Why is my server getting culled?

If your server is getting shut down when you don't want it do, the question to ask is: what are you doing that _should_ be registered as activity?
It could be that your deployment has set a max age (usually in hours or days), and no amount of activity will keep it alive.
It could be that the idle timeout is too short, and doesn't tolerate you sitting and reading and thinking without clicking buttons and running code.
These are tuning parameters in the deployment, and often aren't easy for users to work around.

```{note}
Administrators - because idle timeounts and max age are settings that directly affects users,
make sure it is documented in your user documentation for your deployment,
for example as [2i2c does here](https://docs.2i2c.org/admin/user-management/control-user-server/#stop-user-servers-after-inactivity).
```

#### Keeping a server alive

If you have started a long-running task that you want to keep going, there are a lot of ways to try to fake activity, but the best is probably to be explicit about keeping your server alive.
[jupyter-keepalive](https://github.com/minrk/jupyter-keepalive) is an Extension that relies on Jupyter Server's extensible last_activity sources which provides a mechanism for users to ensure that a server will be considered 'active' for some interval.
This avoids the need to try to somehow trigger other forms of activity to keep a server alive,
such as running a pointless execution or leaving a browser open overnight.
