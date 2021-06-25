# Scopes in JupyterHub

A scope has a syntax-based design that reveals which resources it provides access to. Resources are objects with a type, associated data, relationships to other resources, and a set of methods that operate on them (see [RESTful API](https://restful-api-design.readthedocs.io/en/latest/resources.html) documentation for more information).

`<resource>` in the RBAC scope design refers to the resource name in the [JupyterHub's API](../reference/rest-api.rst) endpoints in most cases. For instance, `<resource>` equal to `users` corresponds to JupyterHub's API endpoints beginning with _/users_.

(scope-conventions-target)=

## Scope conventions

- `<resource>` \
  The top-level `<resource>` scopes, such as `users` or `groups`, grant read and write permissions to the resource itself as well as its sub-resources. For example, the scope `users:activity` is included in the scope `users`.

- `read:<resource>` \
  Limits permissions to read-only operations on the resource.

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
2. default token scope `all`.

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

The token metascope `all` covers the same scopes as the token owner's scopes during requests. For example, if a token owner has roles containing the scopes `read:groups` and `read:users`, the `all` scope resolves to the set of scopes `{read:groups, read:users}`.

If the token owner has default `user` role, the `all` scope resolves to `self`, which will subsequently be expanded to include all the user-specific scopes (or empty set in the case of services).

If the token owner is a member of any group with roles, the group scopes will also be included in resolving the `all` scope.

(horizontal-filtering-target)=

## Horizontal filtering

Horizontal filtering, also called _resource filtering_, is the concept of reducing the payload of an API call to cover only the subset of the _resources_ that the scopes of the client provides them access to.
Requested resources are filtered based on the filter of the corresponding scope. For instance, if a service requests a user list (guarded with scope `read:users`) with a role that only contains scopes `read:users!user=hannah` and `read:users!user=ivan`, the returned list of user models will be an intersection of all users and the collection `{hannah, ivan}`. In case this intersection is empty, the API call returns an HTTP 404 error, regardless if any users exist outside of the clients scope filter collection.

In case a user resource is being accessed, any scopes with _group_ filters will be expanded to filters for each _user_ in those groups.

### `!user` filter

The `!user` filter is a special horizontal filter that strictly refers to the **"owner only"** scopes, where _owner_ is a user entity. The filter resolves internally into `!user=<ownerusername>` ensuring that only the owner's resources may be accessed through the associated scopes.

For example, the `server` role assigned by default to server tokens contains `access:servers!user` and `users:activity!user` scopes. This allows the token to access and post activity of only the servers owned by the token owner.

The filter can be applied to any scope.

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

```{Caution}
Note that only the {ref}`horizontal filtering <horizontal-filtering-target>` can be added to scopes to customize them. \
Metascopes `self` and `all`, `<resource>`, `<resource>:<subresource>`, `read:<resource>`, `admin:<resource>`, and `access:<resource>` scopes are predefined and cannot be changed otherwise.
```

### Scopes and APIs

The scopes are also listed in the [](../reference/rest-api.rst) documentation. Each API endpoint has a list of scopes which can be used to access the API; if no scopes are listed, the API is not authenticated and can be accessed without any permissions (i.e., no scopes).

Listed scopes by each API endpoint reflect the "lowest" permissions required to gain any access to the corresponding API. For example, posting user's activity (_POST /users/:name/activity_) needs `users:activity` scope. If scope `users` is passed during the request, the access will be granted as the required scope is a subscope of the `users` scope. If, on the other hand, `read:users:activity` scope is passed, the access will be denied.
