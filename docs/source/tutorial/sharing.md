# Sharing access to user servers

In order to make use of features like JupyterLab's real-time collaboration (RTC), multiple users must have access to a single server.
There are a few ways to do this, but ultimately both users must have the appropriate `access:servers` scope.
Prior to JupyterHub 5.0, this could only be granted via static role assignments.
JupyterHub 5.0 adds the concept of a 'share', allowing _users_ to grant each other limited access to their servers.

:::{seealso}
Documentation on [roles and scopes](rbac) for more details on how permissions work in JupyterHub.
:::

In JupyterHub, shares:

1. are 'granted' to a user or group
2. grant only limited permissions (e.g. only 'access' or access and start/stop)
3. may be revoked by anyone with the `admin:shares` permissions
4. (may) expire

Additionally a "share code" is a string, which has all the same properties as a share aside from the user or group.
The code can be exchanged for actual sharing permission, to enable the pattern of sharing permissions without needing to know the username(s) of who you'd like to share with (e.g. email a link).

There is not yet _UI_ to create shares, but they can be managed via JupyterHub's [REST API][].

In general, with shares you can:

1. access other users' servers
2. grant access to your servers
3. see servers shared with you
4. review and revoke permissions for servers you manage

## Share or revoke access to a server

To modify who has access to a server, you need the permission `admin:shares` with the appropriate _server_ filter.
You can only modify access to one server at a time.

Send a PATCH request to `/api/shares/:username/:servername` to modify permissions.
The JSON body should have at

```
PATCH /api/shares/:username/:servername
{
    "scopes": [],
    "grant": {
        "users": ["username"],
        "groups": ["groupname"],
    },
    "revoke": {
        "users": ["username"],
        "groups": ["groupname"],
    }
}
```

Users or groups specified in `grant` will be _granted_ access to the target server.
Users or groups specified in `revoke` will have their access to the target server _revoked_.

At least one of `grant` and `revoke` must be specified.

If `scopes` is specified, all requested scopes _must_ have the `!server=:username/:servername` filter applied.
The default value for `scopes` is `["access:servers!server=:username/:servername"]` (i.e. the 'access scope').

When revoking permissions, _all_ permissions are revoked (scopes).

### Revoke _all_ permissions

To modify who has access to a server, you need the permission `admin:shares` with the appropriate _server_ filter.
A DELETE request will revoke all shared access permissions for the target server.

```
DELETE /api/shares/:username/:servername
```

## View shares for a server

To view shares for a given server, you need the permission `read:shares` with the appropriate _server_ filter.

```
GET /api/shares/:username/:servername
```

This is a paginated endpoint.

## View servers shared with user or group

To review servers shared with a given user or group, you need the permission `read:user:shares` or `read:group:shares` with the appropriate _user_ or _group_ filter.

```
GET /api/users/:username/shares
# or
GET /api/groups/:groupname/shares
```

This is a paginated endpoint.

## The Share model

A Share returned in the REST API has the following structure:

```python
{
    "server": {
        "name": "servername",
        "user": {
          "name": "ownername"
        }
    },
    "scopes": ["access:servers!server=username/servername"],
    "user": { # or null
        "name": "username",
    },
    "group": None, # or {"name": "groupname"},
    "created_at": "2023-10-02T13:27Z",
}
```

where exactly one of `user` and `group` is not null and the other is null.

## Share via invitation code

Sometimes you would like to share access to a server with one or more users,
but you don't want to deal with collecting everyone's username.
For this, you can create shares via _share code_.
This is identical to sharing with a user,
only it adds the step where the sharer creates the _code_ and distributes the code to one or more users,
then the users themselves exchange the code for actual sharing permissions.

Share codes are much like shares, except:

1. they don't associate with specific users
2. they can be used by more than one user (i.e. send one invite email to several recipients)
3. they expire (default: 1 day)

### Creating share codes

To create a share code:

```
POST /api/share-code/:username/:servername
```

where the body should include the scopes to be granted,
and expiration. Share codes _must_ expire, and

TODO: discuss expiration?

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
  "code": "abc13334....",
  "scopes": ["access:servers!server=username/servername"],
  "server": {
    "name": "",
    "user": {
      "name": "",
    },
  },
}

### Accepting sharing invitations

Sharing invitations can be accepted by visiting:

```

/hub/accept-share/:share-code

```

where you will be able to confirm the permissions you would like to accept.
```
