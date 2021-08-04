# Starting servers with the JupyterHub API

JupyterHub's [REST API][] allows launching servers on behalf of users
without ever interacting with the JupyterHub UI.
This allows you to build services launching Jupyter-based services for users
without relying on the JupyterHub UI at all,
enabling a variety of user/launch/lifecycle patterns not natively supported by JupyterHub,
without needing to develop all the server management features of JupyterHub Spawners and/or Authenticators.
[BinderHub][] is an example of such an application.

[binderhub]: https://binderhub.readthedocs.io
[rest api]: ../reference/rest.md

This document provides an example of working with the JupyterHub API to
manage servers for users.
In particular, we will cover how to:

1. [check status of servers](checking)
2. [start servers](starting)
3. [wait for servers to be ready](waiting)
4. [communicate with servers](communicating)
5. [stop servers](stopping)

(checking)=

## Checking server status

Requesting information about a user includes a `servers` field,
which is a dictionary.

```
GET /hub/api/users/:username
```

**Required scope: `read:servers`**

```json
{
  "admin": false,
  "groups": [],
  "pending": null,
  "server": null,
  "name": "test-1",
  "kind": "user",
  "last_activity": "2021-08-03T18:12:46.026411Z",
  "created": "2021-08-03T18:09:59.767600Z",
  "roles": ["user"],
  "servers": {}
}
```

If the `servers` dict is empty, the user has no running servers.
The keys of the `servers` dict are server names as strings.
Many JupyterHub deployments only use the 'default' server,
which has the empty string `''` for a name.
In this case, the servers dict will always have either zero or one elements.

This is the servers dict when the user's default server is fully running and ready:

```json
  "servers": {
    "": {
      "name": "",
      "last_activity": "2021-08-03T18:48:35.934000Z",
      "started": "2021-08-03T18:48:29.093885Z",
      "pending": null,
      "ready": true,
      "url": "/user/test-1/",
      "user_options": {},
      "progress_url": "/hub/api/users/test-1/server/progress"
    }
  }
```

Key properties of a server:

name
: the server's name. Always the same as the key in `servers`

ready
: boolean. If true, the server can be expected to respond to requests at `url`.

pending
: `null` or a string indicating a transitional state (such as `start` or `stop`).
Will always be `null` if `ready` is true,
and will always be a string if `ready` is false.

url
: The server's url (just the path, e.g. `/users/:name/:servername/`)
where the server can be accessed if `ready` is true.

progress_url
: The API url path (starting with `/hub/api`)
where the progress API can be used to wait for the server to be ready.
See below for more details on the progress API.

last_activity
: ISO8601 timestamp indicating when activity was last observed on the server

started
: ISO801 timestamp indicating when the server was last started

We've seen the `servers` model with no servers and with one `ready` server.
Here is what it looks like immediately after requesting a server launch,
while the server is not ready yet:

```json
  "servers": {
    "": {
      "name": "",
      "last_activity": "2021-08-03T18:48:29.093885Z",
      "started": "2021-08-03T18:48:29.093885Z",
      "pending": "spawn",
      "ready": false,
      "url": "/user/test-1/",
      "user_options": {},
      "progress_url": "/hub/api/users/test-1/server/progress"
    }
  }
```

Note that `ready` is false and `pending` is `spawn`.
This means that the server is not ready
(attempting to access it may not work)
because it isn't finished spawning yet.
We'll get more into that below in [waiting for a server][].

[waiting for a server]: waiting

(starting)=

## Starting servers

To start a server, make the request

```
POST /hub/api/users/:username/servers/[:servername]
```

**Required scope: `servers`**

(omit servername for the default server)

Assuming the request was valid,
there are two possible responses:

201 Created
: This status code means the launch completed and the server is ready.
It should be available at the server's URL immediately.

202 Accepted
: This is the more likely response,
and means that the server has begun launching,
but isn't immediately ready.
The server has `pending: 'spawn'` at this point.

_Aside: how quickly JupyterHub responds with `202 Accepted` is governed by the `slow_spawn_timeout` tornado setting._

(waiting)=

## Waiting for a server

If you are starting a server via the API,
there's a good change you want to know when it's ready.
There are two ways to do with:

1. {ref}`Polling the server model <polling>`
2. the {ref}`progress API <progress>`

(polling)=

### Polling the server model

The simplest way to check if a server is ready
is to request the user model.

If:

1. the server name is in the user's `servers` model, and
2. `servers['servername']['ready']` is true

A Python example, checking if a server is ready:

```python
def server_ready(hub_url, user, server_name="", token):
    r = requests.get(
        f"{hub_url}/hub/api/users/{user}/servers/{server_name}",
        headers={"Authorization": f"token {token}"},
    )
    r.raise_for_status()
    user_model = r.json()
    servers = user_model.get("servers", {})
    if server_name not in servers:
        return False

    server = servers[server_name]
    if server['ready']:
        print(f"Server {user}/{server_name} ready at {server['url']}")
        return True
    else:
        print(f"Server {user}/{server_name} not ready, pending {server['pending']}")
        return False
```

You can keep making this check until `ready` is true.

(progress)=

### Progress API

The most _efficient_ way to wait for a server to start is the progress API.

The progress URL is available in the server model under `progress_url`,
and has the form `/hub/api/users/:user/servers/:servername/progress`.

_the default server progress can be accessed at `:user/servers//progress` or `:user/server/progress`_

```
GET /hub/api/users/:user/servers/:servername/progress
```

**Required scope: `read:servers`**

This is an [EventStream][] API.
In an event stream, messages are _streamed_ and delivered on lines of the form:

```
data: {"progress": 10, "message": "...", ...}
```

where the line after `data:` contains a JSON-serialized dictionary.
Lines that do not start with `data:` should be ignored.

[eventstream]: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#examples

progress events have the form:

```python
{
    "progress": 0-100,
    "message": "",
    "ready": True, # or False

}
```

progress
: integer, 0-100

message
: string message describing progress stages

ready
: present and true only for the last event when the server is ready

url
: only present if `ready` is true; will be the server's url

the progress API can be used even with fully ready servers.
If the server is ready,
there will only be one event that looks like:

```json
{
  "progress": 100,
  "ready": true,
  "message": "Server ready at /user/test-1/",
  "html_message": "Server ready at <a href=\"/user/test-1/\">/user/test-1/</a>",
  "url": "/user/test-1/"
}
```

where `ready` and `url` are the same as in the server model (`ready` will always be true).

A typical complete stream from the event-stream API:

```

data: {"progress": 0, "message": "Server requested"}

data: {"progress": 50, "message": "Spawning server..."}

data: {"progress": 100, "ready": true, "message": "Server ready at /user/test-user/", "html_message": "Server ready at <a href=\"/user/test-user/\">/user/test-user/</a>", "url": "/user/test-user/"}
```

Here is a Python example for consuming an event stream:

```{literalinclude} ../../../examples/server-api/start-stop-server.py
:language: python
:pyobject: event_stream
```

(stopping)=

## Stopping servers

Servers can be stopped with a DELETE request:

```
DELETE /hub/api/users/:user/servers/[:servername]
```

**Required scope: `servers`**

Like start, delete may not complete immediately.
The DELETE request has two possible response codes:

204 Deleted
: This status code means the delete completed and the server is fully stopped.
It will now be absent from the user `servers` model.

202 Accepted
: Like start, `202` means your request was accepted,
but is not yet complete.
The server has `pending: 'stop'` at this point.

Unlike start, there is no progress API for stop.
To wait for stop to finish, you must poll the user model
and wait for the server to disappear from the user `servers` model.

```{literalinclude} ../../../examples/server-api/start-stop-server.py
:language: python
:pyobject: stop_server
```

(communicating)=

## Communicating with servers

JupyterHub tokens with the the `access:servers` scope
can be used to communicate with servers themselves.
This can be the same token you used to launch your service.

```{note}
Access scopes are new in JupyterHub 2.0.
To access servers in JupyterHub 1.x,
a token must be owned by the same user as the server,
*or* be an admin token if admin_access is enabled.
```

The URL returned from a server model is the url path suffix,
e.g. `/user/:name/` to append to the jupyterhub base URL.

For instance, `{hub_url}{server_url}`,
where `hub_url` would be e.g. `http://127.0.0.1:8000` by default,
and `server_url` `/user/myname`,
for a full url of `http://127.0.0.1:8000/user/myname`.

## Python example

The JupyterHub repo includes a complete example in {file}`examples/server-api`
tying all this together.

To summarize the steps:

1. get user info from `/user/:name`
2. the server model includes a `ready` state to tell you if it's ready
3. if it's not ready, you can follow up with `progress_url` to wait for it
4. if it is ready, you can use the `url` field to link directly to the running server

The example demonstrates starting and stopping servers via the JupyterHub API,
including waiting for them to start via the progress API,
as well as waiting for them to stop via polling the user model.

```{literalinclude} ../../../examples/server-api/start-stop-server.py
:language: python
:start-at: def event_stream
:end-before: def main
```
