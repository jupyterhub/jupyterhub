(jupyterhub-scopes)=

# Scopes in JupyterHub

A scope has a syntax-based design that reveals which resources it provides access to. Resources are objects with a type, associated data, relationships to other resources, and a set of methods that operate on them (see [RESTful API](https://restful-api-design.readthedocs.io/en/latest/resources.html) documentation for more information).

`<resource>` in the RBAC scope design refers to the resource name in the [JupyterHub's API](jupyterhub-rest-API) endpoints in most cases. For instance, `<resource>` equal to `users` corresponds to JupyterHub's API endpoints beginning with _/users_.

(scope-conventions-target)=

## Scope conventions

- `<resource>` \
  The top-level `<resource>` scopes, such as `users` or `groups`, grant read, write, and list permissions to the resource itself as well as its sub-resources. For example, the scope `users:activity` is included in the scope `users`.

- `read:<resource>` \
  Limits permissions to read-only operations on single resources.

- `list:<resource>` \
  Read-only access to listing endpoints.
  Use `read:<resource>:<subresource>` to control what fields are returned.

- `admin:<resource>` \
  Grants additional permissions such as create/delete on the corresponding resource in addition to read and write permissions.

- `access:<resource>` \
  Grants access permissions to the `<resource>` via API or browser.

- `<resource>:<subresource>` \
  The {ref}`vertically filtered <vertical-filtering-target>` scopes provide access to a subset of the information granted by the `<resource>` scope. E.g., the scope `users:activity` only provides permission to post user activity.

- `<resource>!<object>=<objectname>` \
  {ref}`horizontal-filtering-target` is implemented by the `!<object>=<objectname>`scope structure. A resource (or sub-resource) can be filtered based on `user`, `server`, `group` or `service` name. For instance, `<resource>!user=charlie` limits access to only return resources of user `charlie`. \
  Only one filter per scope is allowed, but filters for the same scope have an additive effect; a larger filter can be used by supplying the scope multiple times with different filters.

By adding a scope to an existing role, all role bearers will gain the associated permissions.

## Metascopes

Metascopes do not follow the general scope syntax. Instead, a metascope resolves to a set of scopes, which can refer to different resources, based on their owning entity. In JupyterHub, there are currently two metascopes:

1. default user scope `self`, and
2. default token scope `inherit`.

(default-user-scope-target)=

### Default user scope

Access to the user's own resources and subresources is covered by metascope `self`. This metascope includes the user's model, activity, servers and tokens. For example, `self` for a user named "gerard" includes:

- `users!user=gerard` where the `users` scope provides access to the full user model and activity. The filter restricts this access to the user's own resources.
- `servers!user=gerard` which grants the user access to their own servers without being able to create/delete any.
- `tokens!user=gerard` which allows the user to access, request and delete their own tokens.
- `access:servers!user=gerard` which allows the user to access their own servers via API or browser.

The `self` scope is only valid for user entities. In other cases (e.g., for services) it resolves to an empty set of scopes.

(default-token-scope-target)=

### Default token scope

The token metascope `inherit` causes the token to have the same permissions as the token's owner. For example, if a token owner has roles containing the scopes `read:groups` and `read:users`, the `inherit` scope resolves to the set of scopes `{read:groups, read:users}`.

If the token owner has default `user` role, the `inherit` scope resolves to `self`, which will subsequently be expanded to include all the user-specific scopes (or empty set in the case of services).

If the token owner is a member of any group with roles, the group scopes will also be included in resolving the `inherit` scope.

(horizontal-filtering-target)=

## Horizontal filtering

Horizontal filtering, also called _resource filtering_, is the concept of reducing the payload of an API call to cover only the subset of the _resources_ that the scopes of the client provides them access to.
Requested resources are filtered based on the filter of the corresponding scope. For instance, if a service requests a user list (guarded with scope `read:users`) with a role that only contains scopes `read:users!user=hannah` and `read:users!user=ivan`, the returned list of user models will be an intersection of all users and the collection `{hannah, ivan}`. In case this intersection is empty, the API call returns an HTTP 404 error, regardless if any users exist outside of the clients scope filter collection.

In case a user resource is being accessed, any scopes with _group_ filters will be expanded to filters for each _user_ in those groups.

(self-referencing-filters)=

### Self-referencing filters

There are some 'shortcut' filters,
which can be applied to all scopes,
that filter based on the entities associated with the request.

The `!user` filter is a special horizontal filter that strictly refers to the **"owner only"** scopes, where _owner_ is a user entity. The filter resolves internally into `!user=<ownerusername>` ensuring that only the owner's resources may be accessed through the associated scopes.

For example, the `server` role assigned by default to server tokens contains `access:servers!user` and `users:activity!user` scopes. This allows the token to access and post activity of only the servers owned by the token owner.

:::{versionadded} 3.0
`!service` and `!server` filters.
:::

In addition to `!user`, _tokens_ may have filters `!service`
or `!server`, which expand similarly to `!service=servicename`
and `!server=servername`.
This only applies to tokens issued via the OAuth flow.
In these cases, the name is the _issuing_ entity (a service or single-user server),
so that access can be restricted to the issuing service,
e.g. `access:servers!server` would grant access only to the server that requested the token.

These filters can be applied to any scope.

(vertical-filtering-target)=

## Vertical filtering

Vertical filtering, also called _attribute filtering_, is the concept of reducing the payload of an API call to cover only the _attributes_ of the resources that the scopes of the client provides them access to. This occurs when the client scopes are subscopes of the API endpoint that is called.
For instance, if a client requests a user list with the only scope being `read:users:groups`, the returned list of user models will contain only a list of groups per user.
In case the client has multiple subscopes, the call returns the union of the data the client has access to.

The payload of an API call can be filtered both horizontally and vertically simultaneously. For instance, performing an API call to the endpoint `/users/` with the scope `users:name!user=juliette` returns a payload of `[{name: 'juliette'}]` (provided that this name is present in the database).

(available-scopes-target)=

## Available scopes

Table below lists all available scopes and illustrates their hierarchy. Indented scopes indicate subscopes of the scope(s) above them.

There are four exceptions to the general {ref}`scope conventions <scope-conventions-target>`:

- `read:users:name` is a subscope of both `read:users` and `read:servers`. \
  The `read:servers` scope requires access to the user name (server owner) due to named servers distinguished internally in the form `!server=username/servername`.

- `read:users:activity` is a subscope of both `read:users` and `users:activity`. \
  Posting activity via the `users:activity`, which is not included in `users` scope, needs to check the last valid activity of the user.

- `read:roles:users` is a subscope of both `read:roles` and `admin:users`. \
  Admin privileges to the _users_ resource include the information about user roles.

- `read:roles:groups` is a subscope of both `read:roles` and `admin:groups`. \
  Similar to the `read:roles:users` above.

```{include} scope-table.md

```

:::{versionadded} 3.0
The `admin-ui` scope is added to explicitly grant access to the admin page,
rather than combining `admin:users` and `admin:servers` permissions.
This means a deployment can enable the admin page with only a subset of functionality enabled.

Note that this means actions to take _via_ the admin UI
and access _to_ the admin UI are separated.
For example, it generally doesn't make sense to grant
`admin-ui` without at least `list:users` for at least some subset of users.

For example:

```python
c.JupyterHub.load_roles = [
  {
    "name": "instructor-data8",
    "scopes": [
      # access to the admin page
      "admin-ui",
      # list users in the class group
      "list:users!group=students-data8",
      # start/stop servers for users in the class
      "admin:servers!group=students-data8",
      # access servers for users in the class
      "access:servers!group=students-data8",
    ],
    "group": ["instructors-data8"],
  }
]
```

will grant instructors in the data8 course permission to:

1. view the admin UI
2. see students in the class (but not all users)
3. start/stop/access servers for users in the class
4. but _not_ permission to administer the users themselves (e.g. change their permissions, etc.)
   :::

```{Caution}
Note that only the {ref}`horizontal filtering <horizontal-filtering-target>` can be added to scopes to customize them. \
Metascopes `self` and `all`, `<resource>`, `<resource>:<subresource>`, `read:<resource>`, `admin:<resource>`, and `access:<resource>` scopes are predefined and cannot be changed otherwise.
```

(access-scopes)=

### Access scopes

An **access scope** is used to govern _access_ to a JupyterHub service or a user's single-user server.
This means making API requests, or visiting via a browser using OAuth.
Without the appropriate access scope, a user or token should not be permitted to make requests of the service.

When you attempt to access a service or server authenticated with JupyterHub, it will begin the [oauth flow](explanation:hub-oauth) for issuing a token that can be used to access the service.
If the user does not have the access scope for the relevant service or server, JupyterHub will not permit the oauth process to complete.
If oauth completes, the token will have at least the access scope for the service.
For minimal permissions, this is the _only_ scope granted to tokens issued during oauth by default,
but can be expanded via {attr}`.Spawner.oauth_client_allowed_scopes` or a service's [`oauth_client_allowed_scopes`](service-credentials) configuration.

:::{seealso}
[Further explanation of OAuth in JupyterHub](explanation:hub-oauth)
:::

If a given service or single-user server can be governed by a single boolean "yes, you can use this service" or "no, you can't," or limiting via other existing scopes, access scopes are enough to manage access to the service.
But you can also further control granular access to servers or services with [custom scopes](custom-scopes), to limit access to particular APIs within the service, e.g. read-only access.

#### Example access scopes

Some example access scopes for services:

access:services
: access to all services

access:services!service=somename
: access to the service named `somename`

and for user servers:

access:servers
: access to all user servers

access:servers!user
: access to all of a user's _own_ servers (never in _resolved_ scopes, but may be used in configuration)

access:servers!user=name
: access to all of `name`'s servers

access:servers!group=groupname
: access to all servers owned by a user in the group `groupname`

access:servers!server
: access to only the issuing server (only relevant when applied to oauth tokens associated with a particular server, e.g. via the {attr}`Spawner.oauth_client_allowed_scopes` configuration.

access:servers!server=username/
: access to only `username`'s _default_ server.

(granting-scopes)=

### Considerations when allowing users to grant permissions via the `groups` scope

In general, permissions are fixed by role assignments in configuration (or via [Authenticator-managed roles](#authenticator-roles) in JupyterHub 5) and can only be modified by administrators who can modify the Hub configuration.

There is only one scope that allows users to modify permissions of themselves or others at runtime instead of via configuration:
the `groups` scope, which allows adding and removing users from one or more groups.
With the `groups` scope, a user can add or remove any users to/from any group.
With the `groups!group=name` filtered scope, a user can add or remove any users to/from a specific group.
There are two ways in which adding a user to a group may affect their permissions:

- if the group is assigned one or more roles, adding a user to the group may increase their permissions (this is usually the point!)
- if the group is the _target_ of a filter on this or another group, such as `access:servers!group=students`, adding a user to the group can grant _other_ users elevated access to that user's resources.

With these in mind, when designing your roles, do not grant users the `groups` scope for any groups which:

- have roles the user should not have authority over, or
- would grant them access they shouldn't have for _any_ user (e.g. don't grant `teachers` both `access:servers!group=students` and `groups!group=students` which is tantamount to the unrestricted `access:servers` because they control which users the `group=students` filter applies to).

If a group does not have role assignments and the group is not present in any `!group=` filter, there should be no permissions-related consequences for adding users to groups.

:::{note}
The legacy `admin` property of users, which grants extreme superuser permissions and is generally discouraged in favor of more specific roles and scopes, may be modified only by other users with the `admin` property (e.g. added via `admin_users`).
:::

(custom-scopes)=

### Custom scopes

:::{versionadded} 3.0
:::

JupyterHub 3.0 introduces support for custom scopes.
Services that use JupyterHub for authentication and want to implement their own granular access may define additional _custom_ scopes and assign them to users with JupyterHub roles.

% Note: keep in sync with pattern/description in jupyterhub/scopes.py

Custom scope names must start with `custom:`
and contain only lowercase ascii letters, numbers, hyphen, underscore, colon, and asterisk (`-_:*`).
The part after `custom:` must start with a letter or number.
Scopes may not end with a hyphen or colon.

The only strict requirement is that a custom scope definition must have a `description`.
It _may_ also have `subscopes` if you are defining multiple scopes that have a natural hierarchy,

For example:

```python
c.JupyterHub.custom_scopes = {
    "custom:myservice:read": {
        "description": "read-only access to myservice",
    },
    "custom:myservice:write": {
        "description": "write access to myservice",
        # write permission implies read permission
        "subscopes": [
            "custom:myservice:read",
        ],
    },
}

c.JupyterHub.load_roles = [
    # graders have read-only access to the service
    {
        "name": "service-user",
        "groups": ["graders"],
        "scopes": [
            "custom:myservice:read",
            "access:service!service=myservice",
        ],
    },
    # instructors have read and write access to the service
    {
        "name": "service-admin",
        "groups": ["instructors"],
        "scopes": [
            "custom:myservice:write",
            "access:service!service=myservice",
        ],
    },
]
```

In the above configuration, two scopes are defined:

- `custom:myservice:read` grants read-only access to the service, and
- `custom:myservice:write` grants write access to the service
- write access _implies_ read access via the `subscope`

These custom scopes are assigned to two groups via `roles`:

- users in the group `graders` are granted read access to the service
- users in the group `instructors` are
- both are granted _access_ to the service via `access:service!service=myservice`

When the service completes OAuth, it will retrieve the user model from `/hub/api/user`.
This model includes a `scopes` field which is a list of authorized scope for the request,
which can be used.

```python
def require_scope(scope):
    """decorator to require a scope to perform an action"""
    def wrapper(func):
        @functools.wraps(func)
        def wrapped_func(request):
            user = fetch_hub_api_user(request.token)
            if scope not in user["scopes"]:
                raise HTTP403(f"Requires scope {scope}")
            else:
                return func()
    return wrapper

@require_scope("custom:myservice:read")
async def read_something(request):
    ...

@require_scope("custom:myservice:write")
async def write_something(request):
    ...
```

If you use {class}`~.HubOAuthenticated`, this check is performed automatically
against the `.hub_scopes` attribute of each Handler
(the default is populated from `$JUPYTERHUB_OAUTH_ACCESS_SCOPES` and usually `access:services!service=myservice`).

:::{versionchanged} 3.0
The JUPYTERHUB_OAUTH_SCOPES environment variable is deprecated and renamed to JUPYTERHUB_OAUTH_ACCESS_SCOPES,
to avoid ambiguity with JUPYTERHUB_OAUTH_CLIENT_ALLOWED_SCOPES
:::

```python
from tornado import web
from jupyterhub.services.auth import HubOAuthenticated

class MyHandler(HubOAuthenticated, BaseHandler):
    hub_scopes = ["custom:myservice:read"]

    @web.authenticated
    def get(self):
        ...
```

Existing scope filters (`!user=`, etc.) may be applied to custom scopes.
Custom scope _filters_ are NOT supported.

:::{warning}
JupyterHub allows you to define custom scopes,
but it does not enforce that your services apply them.

For example, if you enable read-only access to servers via custom JupyterHub
(as seen in the `read-only` example),
it is the administrator's responsibility to enforce that they are applied.
If you allow users to launch servers without that custom Authorizer,
read-only permissions will not be enforced, and the default behavior of unrestricted access via the `access:servers` scope will be applied.
:::

### Scopes and APIs

The scopes are also listed in the [](jupyterhub-rest-API) documentation.
Each API endpoint has a list of scopes which can be used to access the API;
if no scopes are listed, the API is not authenticated and can be accessed without any permissions (i.e., no scopes).

Listed scopes by each API endpoint reflect the "lowest" permissions required to gain any access to the corresponding API.
For example, posting user's activity (_POST /users/:name/activity_) needs `users:activity` scope.
If scope `users` is held by the request, the access will be granted as the required scope is a subscope of the `users` scope.
If, on the other hand, `read:users:activity` scope is the only scope held, the request will be denied.
