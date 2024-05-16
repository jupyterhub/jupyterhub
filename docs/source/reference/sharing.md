(sharing-reference)=

# Sharing access to user servers

In order to make use of features like JupyterLab's real-time collaboration (RTC), multiple users must have access to a single server.
There are a few ways to do this, but ultimately both users must have the appropriate `access:servers` scope.
Prior to JupyterHub 5.0, this could only be granted via static role assignments in JupyterHub configuration.
JupyterHub 5.0 adds the concept of a 'share', allowing _users_ to grant each other limited access to their servers.

:::{seealso}
Documentation on [roles and scopes](rbac) for more details on how permissions work in JupyterHub, and in particular [access scopes](access-scopes).
:::

In JupyterHub, shares:

1. are 'granted' to a user or group
2. grant only limited permissions (e.g. only 'access' or access and start/stop)
3. may be revoked by anyone with the `shares` permissions
4. may always be revoked by the shared-with user or group

Additionally a "share code" is a random string, which has all the same properties as a Share aside from the user or group.
The code can be exchanged for actual sharing permission, to enable the pattern of sharing permissions without needing to know the username(s) of who you'd like to share with (e.g. email a link).

There is not yet _UI_ to create shares, but they can be managed via JupyterHub's [REST API](jupyterhub-rest-api).

In general, with shares you can:

1. access other users' servers
2. grant access to your servers
3. see servers shared with you
4. review and revoke permissions for servers you manage

## Enable sharing

For safety, users do not have permission to share access to their servers by default.
To grant this permission, a user must have the `shares` scope for their servers.
To grant all users permission to share access to their servers:

```python
c.JupyterHub.load_roles = [
    {
        "name": "user",
        "scopes": ["self", "shares!user"],
    },
]
```

With this, only the sharing via invitation code described below will be available.

Additionally, to share access with a **specific user or group** (more below),
a user must have permission to read that user or group's name.
To enable the _full_ sharing API for all users:

```python
c.JupyterHub.load_roles = [
    {
        "name": "user",
        "scopes": ["self", "shares!user", "read:users:name", "read:groups:name"],
    },
]
```

Note that this exposes the ability for all users to _discover_ existing user and group names,
which is part of why we have the share-by-code pattern,
so users don't need this ability to share with each other.

## Share or revoke access to a server

To modify who has access to a server, you need the permission `shares` with the appropriate _server_ filter,
and access to read the name of the target user or group (`read:users:name` or `read:groups:name`).
You can only modify access to one server at a time.

### Granting access to a server

To grant access to a particular user, in addition to `shares`, the granter must have at least `read:user:name` permission for the target user (or `read:group:name` if it's a group).

Send a POST request to `/api/shares/:username/:servername` to grant permissions.

```{parsed-literal}
[POST /api/shares/:username/:servername](rest-api-post-shares-server)
```

The JSON body should specify what permissions to grant and whom to grant them to:

```python
{
    "scopes": [],
    "user": "username", # or:
    "group": "groupname",
}
```

It should have exactly one of "user" or "group" defined (not both).
The specified user or group will be _granted_ access to the target server.

If `scopes` is specified, all requested scopes _must_ have the `!server=:username/:servername` filter applied.
The default value for `scopes` is `["access:servers!server=:username/:servername"]` (i.e. the 'access scope' for the server).

### Revoke access

To revoke permissions, you need the permission `shares` with the appropriate _server_ filter,
and `read:users:name` (or `read:groups:name`) for the user or group to modify.
You can only modify access to one server at a time.

Send a PATCH request to `/api/shares/:username/:servername` to revoke permissions.

```{parsed-literal}
[PATCH /api/shares/:username/:servername](rest-api-patch-shares-server)
```

The JSON body should specify the scopes to revoke

```
POST /api/shares/:username/:servername
{
    "scopes": [],
    "user": "username", # or:
    "group": "groupname",
}
```

If `scopes` is empty or unspecified, _all_ scopes are revoked from the target user or group.

#### Revoke _all_ permissions

A DELETE request will revoke all shared access permissions for the given server.

```{parsed-literal}
[DELETE /api/shares/:username/:servername](rest-api-delete-shares-server)
```

### View shares for a server

To view shares for a given server, you need the permission `read:shares` with the appropriate _server_ filter.

```{parsed-literal}
[GET /api/shares/:username/:servername](rest-api-get-shares-server)
```

This is a paginated endpoint, so responses has `items` as a list of Share models, and `_pagination` for information about retrieving all shares if there are many:

```python
{
  "items": [
    {
      "server": {...},
      "scopes": ["access:servers!server=sharer/"],
      "user": {
        "name": "shared-with",
      },
      "group": None, # or {"name": "groupname"},
      ...
    },
    ...
  ],
  "_pagination": {
    "total": 5,
    "limit": 50,
    "offset": 0,
    "next": None,
  },
}
```

see the [rest-api](rest-api-get-shares-server) for full details of the response models.

### View servers shared with user or group

To review servers shared with a given user or group, you need the permission `read:users:shares` or `read:groups:shares` with the appropriate _user_ or _group_ filter.

```{parsed-literal}
[GET /api/users/:username/shared](rest-api-get-user-shared)
```

or

```{parsed-literal}
[GET /api/groups/:groupname/shared](rest-api-get-group-shared)
```

These are paginated endpoints.

### Access permission for a single user on a single server

```{parsed-literal}
[GET /api/users/:username/shared/:ownername/:servername](rest-api-get-user-shared-server)
```

or

```{parsed-literal}
[GET /api/groups/:groupname/shared/:ownername/:servername](rest-api-get-group-shared-server)
```

will return the _single_ Share info for the given user or group for the server specified by `ownername/servername`,
or 404 if no access is granted.

### Revoking one's own permissions for a server

To revoke sharing permissions from the perspective of the user or group being shared with,
you need the permissions `users:shares` or `groups:shares` with the appropriate _user_ or _group_ filter.
This allows users to 'leave' shared servers, without needing permission to manage the server's sharing permissions.

```
[DELETE /api/users/:username/shared/:ownername/:servername](rest-api-delete-user-shared-server)
```

or

```
[DELETE /api/groups/:groupname/shared/:ownername/:servername](rest-api-delete-group-shared-server)
```

will revoke all permissions granted to the user or group for the specified server.

### The Share model

<!-- refresh from examples/user-sharing/rest-api.ipynb -->

A Share returned in the REST API has the following structure:

```python
{
    "server": {
        "name": "servername",
        "user": {
          "name": "ownername"
        },
        "url": "/users/ownername/servername/",
        "ready": True,

    },
    "scopes": ["access:servers!server=username/servername"],
    "user": { # or None
        "name": "username",
    },
    "group": None, # or {"name": "groupname"},
    "created_at": "2023-10-02T13:27Z",
}
```

where exactly one of `user` and `group` is not null and the other is null.

See the [rest-api](rest-api-get-shares-server) for full details of the response models.

## Share via invitation code

Sometimes you would like to share access to a server with one or more users,
but you don't want to deal with collecting everyone's username.
For this, you can create shares via _share code_.
This is identical to sharing with a user,
only it adds the step where the sharer creates the _code_ and distributes the code to one or more users,
then the users themselves exchange the code for actual sharing permissions.

Share codes are much like shares, except:

1. they don't associate with specific users
2. they can be used multiple times, by more than one user (i.e. send one invite email to several recipients)
3. they expire (default: 1 day)
4. they can only be accepted by individual users, not groups

### Creating share codes

To create a share code:

```{parsed-literal}
[POST /api/share-codes/:username/:servername](rest-api-post-share-code)
```

where the body should include the scopes to be granted and expiration.
Share codes _must_ expire.

```python
{
  "scopes": ["access:servers!server=:user/:server"],
  "expires_in": 86400, # seconds, default: 1 day
}
```

If no scopes are specified, the access scope for the specified server will be used.
If no expiration is specified, the code will expire in one day (86400 seconds).

The response contains the code itself:

```python
{
  "code": "abc1234....",
  "accept_url": "/hub/accept-share?code=abc1234",
  "full_accept_url": "https://hub.example.org/hub/accept-share?code=abc1234",
  "id": "sc_1234",
  "scopes": [...],
  ...
}
```

See the [rest-api](rest-api-post-share-code) for full details of the response models.

### Accepting sharing invitations

Sharing invitations can be accepted by visiting:

```
/hub/accept-share/?code=:share-code
```

where you will be able to confirm the permissions you would like to accept.
After accepting permissions, you will be redirected to the running server.

If the server is not running and you have not also been granted permission to start it,
you will need to contact the owner of the server to start it.

### Listing existing invitations

You can see existing invitations for

```{parsed-literal}
[GET /hub/api/share-codes/:username/:servername](rest-api-get-share-codes-server)
```

which produces a paginated list of share codes (_excluding_ the codes themselves, which are not stored by jupyterhub):

```python
{
  "items": [
    {
      "id": "sc_1234",
      "exchange_count": 0,
      "last_exchanged_at": None,
      "scopes": ["access:servers!server=username/servername"],
      "server": {
        "name": "",
        "user": {
          "name": "username",
        },
      },
      ...
    }
  ],
  "_pagination": {
    "total": 5,
    "limit": 50,
    "offset": 0,
    "next": None,
  }
}
```

see the [rest-api](rest-api) for full details of the response models.

### Share code model

<!-- refresh from examples/user-sharing/rest-api.ipynb -->

A Share Code returned in the REST API has most of the same fields as a Share, but lacks the association with a user or group, and adds information about exchanges of the share code,
and the `id` that can be used for revocation:

```python
{

  # common share fields
  "server": {
    "user": {
      "name": "sharer"
    },
    "name": "",
    "url": "/user/sharer/",
    "ready": True,
  },
  "scopes": [
    "access:servers!server=sharer/"
  ],
  # share-code-specific fields
  "id": "sc_1",
  "created_at": "2024-01-23T11:46:32.154416Z",
  "expires_at": "2024-01-24T11:46:32.153582Z",
  "exchange_count": 1,
  "last_exchanged_at": "2024-01-23T11:46:43.589701Z"
}
```

see the [rest-api](rest-api-get-share-codes-server) for full details of the response models.

### Revoking invitations

If you've finished inviting users to a server, you can revoke all invitations with:

```{parsed-literal}
[DELETE /hub/api/share-codes/:username/:servername](rest-api-delete-share-code)
```

or revoke a single invitation code:

```
DELETE /hub/api/share-codes/:username/:servername?code=:thecode
```

You can also revoke a code by _id_, if you non longer have the code:

```
DELETE /hub/api/share-codes/:username/:servername?id=sc_123
```

where the `id` is retrieved from the share-code model, e.g. when listing current share codes.
