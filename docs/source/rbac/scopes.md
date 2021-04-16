# Scopes

A scope has a syntax-based design that reveals which resources it provides access to. Resources are objects with a type, associated data, relationships to other resources, and a set of methods that operate on them (see [RESTful API](https://restful-api-design.readthedocs.io/en/latest/resources.html) documentation for more information).

`<resource>` in the RBAC scope design refers to the resource name in the [JupyterHub's API](../reference/rest-api.rst) endpoints in most cases. For instance, `<resource>` equal to `users` corresponds to JupyterHub's API endpoints beginning with _/users_.

## Scope syntax

- `<resource>` \
  The `<resource>` scopes, such as `users` or `groups`, grant read and write permissions to the resource itself and all its sub-resources. E.g., the scope `users:servers` is included within the scope `users`.
  +++

- `read:<resource>` \
  Limits permissions to read-only operations on the resource.
  +++

- `admin:<resource>` \
  Grants create/delete permissions on the corresponding resource in addition to read and write permissions.
  +++

- `<resource>:<subresource>` \
  The {ref}`vertically filtered <vertical-filtering-target>` scopes provide access to a subset of the information granted by the `<resource>` scope. E.g., the scope `users:servers` allows for accessing user servers only.
  +++

- `<resource>!<object>=<objectname>` \
  {ref}`horizontal-filtering-target` is implemented by the `!<object>=<objectname>`scope structure. A resource (or sub-resource) can be filtered based on `user`, `server`, `group` or `service` name. For instance, `<resource>!user=charlie` limits access to only return resources of user `charlie`. \
  Only one filter per scope is allowed, but filters for the same scope have an additive effect; a larger filter can be used by supplying the scope multiple times with different filters.

By adding a scope to an existing role, all role bearers will gain the associated permissions.

## Metascopes

Metascopes do not follow the general scope syntax. Instead, a metascope resolves to a set of scopes, which can refer to different resources, based on their owning entity. In JupyterHub, there are currently two metascopes:

1. default user scope `self`, and
2. default token scope `all`.

(default-user-scope-target)=

### Default user scope

Access to the user's own resources and subresources is covered by metascope `self`. This metascope includes the user's model, activity, servers and tokens. For example, `self` for a user named "gerard" includes:

- `users!user=gerard` where the `users` scope provides access to the full user model and activity. The filter restricts this access to the user's own resources.
- `users:servers!user=gerard` which grants the user access to their own servers without being able to create/delete any.
- `users:tokens!user=gerard` which allows the user to access, request and delete their own tokens.

The `self` scope is only valid for user entities. In other cases (e.g., for services) it resolves to an empty set of scopes.

(default-token-scope-target)=

### Default token scope

The token metascope `all` covers the same scopes as the token owner's scopes during requests. For example, if a token owner has roles containing the scopes `read:groups` and `read:users`, the `all` scope resolves to the set of scopes `{read:groups, read:users}`.

If the token owner has default `user` role, the `all` scope resolves to `self`, which will subsequently be expanded to include all the user-specific scopes (or empty set in the case of services).

If the token owner is a member of any group with roles, the group scopes will also be included in resolving the `all` scope.

(horizontal-filtering-target)=

## Horizontal filtering

Horizontal filtering, also called _resource filtering_, is the concept of reducing the payload of an API call to cover only the subset of the _resources_ that the scopes of the client provides them access to.
Requested resources are filtered based on the filter of the corresponding scope. For instance, if a service requests a user list (guarded with scope `read:users`) with a role that only contains scopes `read:users!user=hannah` and `read:users!user=ivan`, the returned list of user models will be an intersection of all users and the collection `{hannah, ivan}`. In case this intersection is empty, the API call returns an HTTP 404 error, regardless if any users exist outside of the clients scope filter collection.

In case a user resource is being accessed, any scopes with _group_ filters will be expanded to filters for each _user_ in those groups.

(vertical-filtering-target)=

## Vertical filtering

Vertical filtering, also called _attribute filtering_, is the concept of reducing the payload of an API call to cover only the _attributes_ of the resources that the scopes of the client provides them access to. This occurs when the client scopes are subscopes of the API endpoint that is called.
For instance, if a client requests a user list with the only scope being `read:users:groups`, the returned list of user models will contain only a list of groups per user.
In case the client has multiple subscopes, the call returns the union of the data the client has access to.

The payload of an API call can be filtered both horizontally and vertically simultaneously. For instance, performing an API call to the endpoint `/users/` with the scope `users:name!user=juliette` returns a payload of `[{name: 'juliette'}]` (provided that this name is present in the database).

(available-scopes-target)=

## Available scopes

Table below lists all available scopes and illustrates their hierarchy. Indented scopes indicate subscopes of the scope(s) above them.

Table 1. Available scopes and their hierarchy
| Scope name | Description |
| :--------- | :---------- |
| (no scope) | Allows for only identifying the owning entity. |
| `self` | Metascope, grants access to user's own resources; resolves to (no scope) for services. |
| `all` | Metascope, valid for tokens only. Grants access to everything that the token's owning entity can do. |
| `admin:users` | Grants read, write, create and delete access to users and their authentication state _but not their servers or tokens._ |
| &nbsp;&nbsp;&nbsp;`admin:users:auth_state` | Grants access to users' authentication state only. |
| &nbsp;&nbsp;&nbsp;`users` | Grants read and write permissions to users' models _apart from servers, tokens and authentication state_. |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`users:activity` | Grants access to read and post users' activity only. |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`read:users` | Read-only access to users' models _apart from servers, tokens and authentication state_. |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`read:users:name` | Read-only access to users' names. |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`read:users:roles` | Read-only access to a list of users' roles names. |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`read:users:groups` | Read-only access to users' groups. |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`read:users:activity` | Read-only access to users' activity. |
| `admin:users:servers` | Grants read, start/stop, create and delete permissions to users' servers and their state. |
| &nbsp;&nbsp;&nbsp;`admin:users:server_state` | Grants access to servers' state only. |
| &nbsp;&nbsp;&nbsp;`users:servers` | Allows for starting/stopping users' servers in addition to read access to their models. _Does not include the server state_. |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`read:users:servers` | Read-only access to users' server models. _Does not include the server state_. |
| `users:tokens` | Grants read, write, create and delete permissions to users' tokens. |
| &nbsp;&nbsp;&nbsp;`read:users:tokens` | Read-only access to users' tokens. |
| `admin:groups` | Grants read, write, create and delete access to groups. |
| &nbsp;&nbsp;&nbsp;`groups` | Grants read and write permissions to groups, including adding/removing users to/from groups. |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`read:groups` | Read-only access to groups. |
| `read:services` | Read-only access to service models. |
| &nbsp;&nbsp;&nbsp;`read:services:name` | Read-only access to service names. |
| &nbsp;&nbsp;&nbsp;`read:services:roles` | Read-only access to a list of service roles names. |
| `read:hub` | Read-only access to detailed information about the Hub. |
| `proxy` | Allows for obtaining information about the proxy's routing table, for syncing the Hub with proxy and notifying the Hub about a new proxy. |
| `shutdown` | Grants access to shutdown the hub. |

```{Caution}
Note that only the {ref}`horizontal filtering <horizontal-filtering-target>` can be added to scopes to customize them. \
Metascopes `self` and `all`, `<resource>`, `<resource>:<subresource>`, `read:<resource>` and `admin:<resource>` scopes are predefined and cannot be changed otherwise.
```

### Scopes and APIs

The scopes are also listed in the [](../reference/rest-api.rst) documentation. Each API endpoint has a list of scopes which can be used to access the API; if no scopes are listed, the API is not authenticated and can be accessed without any permissions (i.e., no scopes).

Listed scopes by each API endpoint reflect the "lowest" permissions required to gain any access to the corresponding API. For example, posting user's activity (_POST /users/:name/activity_) needs `users:activity` scope. If scope `users` is passed during the request, the access will be granted as the required scope is a subscope of the `users` scope. If, on the other hand, `read:users:activity` scope is passed, the access will be denied.
