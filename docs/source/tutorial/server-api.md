# Starting servers with the JupyterHub API

Sometimes, when working with applications such as [BinderHub](https://binderhub.readthedocs.io), it may be necessary to launch Jupyter-based services on behalf of your users.
Doing so can be achieved through JupyterHub's [REST API](howto:rest-api), which allows one to launch and manage servers on behalf of users through API calls instead of the JupyterHub UI.
This way, you can take advantage of other user/launch/lifecycle patterns that are not natively supported by the JupyterHub UI, all without the need to develop the server management features of JupyterHub Spawners and/or Authenticators.

This tutorial goes through working with the JupyterHub API to manage servers for users.
In particular, it covers how to:

1. [Check the status of servers](checking)
2. [Start servers](starting)
3. [Wait for servers to be ready](waiting)
4. [Communicate with servers](communicating)
5. [Stop servers](stopping)

At the end, we also provide sample Python code that can be used to implement these steps.

(checking)=

## Checking server status

First, request information about a particular user using a GET request:

```
GET /hub/api/users/:username
```

The response you get will include a `servers` field, which is a dictionary, as shown in this JSON-formatted response:

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

Many JupyterHub deployments only use a 'default' server, represented as an empty string `''` for a name. An investigation of the `servers` field can yield one of two results. First, it can be empty as in the sample JSON response above. In such a case, the user has no running servers.

However, should the user have running servers, then the returned dict should contain various information, as shown in this response:

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
: the server's name. Always the same as the key in `servers`.

ready
: boolean. If true, the server can be expected to respond to requests at `url`.

pending
: `null` or a string indicating a transitional state (such as `start` or `stop`).
Will always be `null` if `ready` is true or a string if false.

url
: The server's url path (e.g. `/users/:name/:servername/`) where the server can be accessed if `ready` is true.

progress_url
: The API URL path (starting with `/hub/api`) where the progress API can be used to wait for the server to be ready.

last_activity
: ISO8601 timestamp indicating when activity was last observed on the server.

started
: ISO801 timestamp indicating when the server was last started.

The two responses above are from a user with no servers and another with one `ready` server. The sample below is a response likely to be received when one requests a server launch while the server is not yet ready:

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

Note that `ready` is `false` and `pending` has the value `spawn`, meaning that the server is not ready and attempting to access it may not work as it is still in the process of spawning. We'll get more into this below in [waiting for a server][].

[waiting for a server]: waiting

(starting)=

## Starting servers

To start a server, make this API request:

```
POST /hub/api/users/:username/servers/[:servername]
```

**Required scope: `servers`**

Assuming the request was valid, there are two possible responses:

201 Created
: This status code means the launch completed and the server is ready and is available at the server's URL immediately.

202 Accepted
: This is the more likely response, and means that the server has begun launching,
but is not immediately ready. As a result, the server shows `pending: 'spawn'` at this point and you should wait for it to start.

(waiting)=

## Waiting for a server to start

After receiving a `202 Accepted` response, you have to wait for the server to start.
Two approaches can be applied to establish when the server is ready:

1. {ref}`Polling the server model <polling>`
2. {ref}`Using the progress API <progress>`

(polling)=

### Polling the server model

The simplest way to check if a server is ready is to programmatically query the server model until two conditions are true:

1. The server name is contained in the `servers` response, and
2. `servers['servername']['ready']` is true.

The Python code snippet below can be used to check if a server is ready:

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

### Using the progress API

The most _efficient_ way to wait for a server to start is by using the progress API.
The progress URL is available in the server model under `progress_url` and has the form `/hub/api/users/:user/servers/:servername/progress`.

The default server progress can be accessed at `:user/servers//progress` or `:user/server/progress` as demonstrated in the following GET request:

```
GET /hub/api/users/:user/servers/:servername/progress
```

**Required scope: `read:servers`**

The progress API is an example of an [EventStream][] API.
Messages are _streamed_ and delivered in the form:

```
data: {"progress": 10, "message": "...", ...}
```

where the line after `data:` contains a JSON-serialized dictionary.
Lines that do not start with `data:` should be ignored.

[eventstream]: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#examples

Progress events have the form:

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
: only present if `ready` is true; will be the server's URL

The progress API can be used even with fully ready servers.
If the server is ready, there will only be one event, which will look like:

```json
{
  "progress": 100,
  "ready": true,
  "message": "Server ready at /user/test-1/",
  "html_message": "Server ready at <a href=\"/user/test-1/\">/user/test-1/</a>",
  "url": "/user/test-1/"
}
```

where `ready` and `url` are the same as in the server model, and `ready` will always be true.

A significant advantage of the progress API is that it shows the status of the server through a stream of messages.
Below is an example of a typical complete stream from the API:

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

Similar to when starting a server, issuing the DELETE request above might not stop the server immediately.
Instead, the DELETE request has two possible response codes:

204 Deleted
: This status code means the delete completed and the server is fully stopped.
It will now be absent from the user `servers` model.

202 Accepted
: This code means your request was accepted but is not yet completely processed.
The server has `pending: 'stop'` at this point.

There is no progress API for checking when a server actually stops.
The only way to wait for a server to stop is to poll it and wait for the server to disappear from the user `servers` model.

This Python code snippet can be used to stop a server and the wait for the process to complete:

```{literalinclude} ../../../examples/server-api/start-stop-server.py
:language: python
:pyobject: stop_server
```

(communicating)=

## Communicating with servers

JupyterHub tokens with the `access:servers` scope can be used to communicate with servers themselves.
The tokens can be the same as those you used to launch your service.

```{note}
Access scopes are new in JupyterHub 2.0.
To access servers in JupyterHub 1.x,
a token must be owned by the same user as the server,
*or* be an admin token if admin_access is enabled.
```

The URL returned from a server model is the URL path suffix,
e.g. `/user/:name/` to append to the jupyterhub base URL.
The returned URL is of the form `{hub_url}{server_url}`,
where `hub_url` would be `http://127.0.0.1:8000` by default and `server_url` is `/user/myname`.
When combined, the two give a full URL of `http://127.0.0.1:8000/user/myname`.

## Python example

The JupyterHub repo includes a complete example in {file}`examples/server-api`
that ties all theses steps together.

In summary, the processes involved in managing servers on behalf of users are:

1. Get user information from `/user/:name`.
2. The server model includes a `ready` state to tell you if it's ready.
3. If it's not ready, you can follow up with `progress_url` to wait for it.
4. If it is ready, you can use the `url` field to link directly to the running server.

The example below demonstrates starting and stopping servers via the JupyterHub API,
including waiting for them to start via the progress API and waiting for them to stop by polling the user model.

```{literalinclude} ../../../examples/server-api/start-stop-server.py
:language: python
:start-at: def event_stream
:end-before: def main
```
