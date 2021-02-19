# Scopes

A scope has a syntax-based design that reveals which resources it provides access to:
- The base`resource` scopes, such as `users` or `groups`, provides non-elevated 'default' read or write permissions to the resource itself and all sub-resources. For instance, the scope`users:servers` is included within the scope`users`.
- The elevated `admin:resource` scopes extend permissions beyond default. For instance, where the scope `users` provides read and write access to user information, the scope `admin:users` allows creating and deleting users.
- The scope structure `resource:subresource` vertical filtering: it provides access to a subset of the information granted by the `resource` scope. For example, the scope `users:names` provides access to user names only.
- The scope structure `read:resource` (or `read:resource:subresource`) limits permissions to read-only operations on `resource` (or `subresource`).
- The scope structure `resource!user=charlie` allows for horizontal filtering: it limits access to only return resources of user `charlie`. Only one filter per scope is allowed, but filters for the same scope have an additive effect; a larger filter can be used by supplying the scope multiple times with different filters.
- A resource can be filtered based on `user`, `server`, `group` or `service` name.
By adding a scope to an existing role, all role bearers will gain the associated permissions.

## Available scopes

[](../reference/rest-api.rst) documentation details all available scopes and which of these are required for what particular API request.

## Standard user scope

The standard user scope `all` provides access to the user's own resources and subresources, including the user's model, activity, servers and tokens. For example, the scope for a user `'gerard'` covers:
- `users!user=gerard` where the `users` scope includes access to the full user model, activity and starting/stopping servers. The filter restricts this access to the user's own resources
- `users:tokens!user=gerard` allows the user to access, request and delete his own tokens only.

(filtering-target)=
## Horizontal filtering

Horizontal filtering, also called *resource filtering*, is the concept of reducing the payload of an API call to cover only the subset of the *resources* that the scopes of the client provides them access to.
Requested resources are filtered based on the filter of the corresponding scope. For instance, if a service requests a user list (guarded with scope `read:users`) with a role that only contains scopes `read:users!user=hannah` and `read:users!user=ivan`, the returned list of user models will be an intersection of all users and the collection `{hannah, ivan}`. In case this intersection is empty, the API call returns an HTTP 404 error, regardless if any users exist outside of the clients scope filter collection.

In case a user resource is being accessed, any scopes with *group* filters will be expanded to filters for each *user* in those groups.

## Vertical filtering

Vertical filtering, also called *attribute filtering*, is the concept of reducing the payload of an API call to cover only the *attributes* of the resources that the scopes of the client provides them access to. This occurs when the client scopes are subscopes of the API endpoint that is called.
For instance, if a client requests a user list with the only scope being `read:user:groups`, the returned list of user models will contain only a list of groups per user.
In case the client has multiple subscopes, the call returns the union of the data the client has access to.


The payload of an API call can be filtered both horizontally and vertically simultaneously. For instance, performing an API call to the endpoint `/users/` with the scope `users:names!user=juliette` returns a payload of `[{name: 'juliette'}]` (provided that this name is present in the database).
