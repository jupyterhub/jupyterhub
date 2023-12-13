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

### Granting access to a server

To grant access to a particular user, in addition to `admin:shares`, the granter must have at least `read:user:name` permission for the target user (or `read:group:name` if it's a group).

Send a POST request to `/api/shares/:username/:servername` to grant permissions.
The JSON body should specify what permissions to grant and whom to grant them to:

```
POST /api/shares/:username/:servername
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

## Revoke access

To revoke permissions, you need the permission `admin:shares` with the appropriate _server_ filter.
You can only modify access to one server at a time.

Send a PATCH request to `/api/shares/:username/:servername` to revoke permissions.
The JSON body should have

```
PATCH /api/shares/:username/:servername
```

```python
{
    "revoke": {
      "users": ["username"],
      "groups": ["groupname"],
    }
}
```

The `revoke` key should be the only top-level key in the body.
When revoking permissions, _all_ permissions are revoked (scopes).
Users or groups specified in `revoke` will have their access to the target server _revoked_.

### Revoke _all_ permissions

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
  "code": "abc13334....",
  "scopes": ["access:servers!server=username/servername"],
  "server": {
    "name": "",
    "user": {
      "name": "",
    },
  },
}
```

### Accepting sharing invitations

Sharing invitations can be accepted by visiting:

```
/hub/accept-share/?code=:share-code
```

where you will be able to confirm the permissions you would like to accept.
After accepting permissions, you will be redirected to the server.
TODO: which may or may not be running!

### Listing existing invitations

You can see existing invitations for

```
GET /hub/api/share-codes/server/:username/:servername
```

which produces:

```

### Revoking invitations

If you've finished inviting users to a server, you can revoke all invitations with:

```

DELETE /hub/api/share-codes/:username/:servername

```

or revoke a single invitation code:

```

DELETE /hub/api/share-codes/:username/:servername?code=:thecode

```

You can also revoke a code by _id_, if you non longer have the code:

```

DELETE /hub/api/share-codes/:username/:servername?id=sc_123

```

```
