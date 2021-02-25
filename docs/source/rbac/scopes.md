# Scopes

A scope has a syntax-based design that reveals which resources it provides access to. Resources are objects with a type, associated data, relationships to other resources, and a set of methods that operate on them (see [RESTful API](https://restful-api-design.readthedocs.io/en/latest/resources.html) documentation for more information). 

`<resource>` in the scope syntax here refers to the resource name in the [JupyterHub's API](../reference/rest-api.rst) endpoints. For instance, `<resource>` equal to `users` corresponds to JupyterHub's API endpoints beginning with _/users_.

## Scope syntax

- `<resource>` \
The `<resource>` scopes, such as `users` or `groups`, grant read and write permissions to the resource itself and all its sub-resources. E.g., the scope `users:servers` is included within the scope `users`.
+++

- `<resource>:<subresource>` \
The {ref}`vertically filtered <vertical-filtering-target>` scopes provide access to a subset of the information granted by the `<resource>` scope. E.g., the scope `users:name` allows for accessing user names only.
+++

- `<resource>!<object>=<objectname>` \
{ref}`horizontal-filtering-target` is implemented by adding `!<object>=<objectname>` to the scope structure. A resource (or subresource) can be filtered based on `user`, `server`, `group` or `service` name. For instance, `<resource>!user=charlie` limits access to only return resources of user `charlie`. \
Only one filter per scope is allowed, but filters for the same scope have an additive effect; a larger filter can be used by supplying the scope multiple times with different filters.
+++

- `read:<resource>` \
Limits permissions to **read-only** operations on the resource. 
+++

- `admin:<resource>` \
Grants **create/delete permissions only** on the corresponding resource. For example, the scope `admin:users` allows creating and deleting users but does not allow for accessing information about existing users or modifying them, which is provided by the scope `users`. 

By adding a scope to an existing role, all role bearers will gain the associated permissions.

## Available scopes

[](../reference/rest-api.rst) documentation lists all available scopes. Each API endpoint has a list of scopes which can be used to access the API. 
```{important} 
Note that only the {ref}`horizontal filtering <horizontal-filtering-target>` can be added to scopes to customize them. `<resource>` scopes, `<resource>:<subresource>`, `read:<resource>` and `admin:<resource>` scopes are predefined and cannot be changed otherwise.
```

(default-user-scope-target)=
## Default user scope

The default user scope `all` provides access to the user's own resources and subresources, including the user's model, activity, servers and tokens. For example, the scope for a user `'gerard'` covers:
- `users!user=gerard` where the `users` scope includes access to the full user model, activity and starting/stopping servers. The horizontal filter restricts this access to the user's own resources.
- `users:tokens!user=gerard` allows the user to access, request and delete his own tokens only.

(horizontal-filtering-target)=
## Horizontal filtering

Horizontal filtering, also called *resource filtering*, is the concept of reducing the payload of an API call to cover only the subset of the *resources* that the scopes of the client provides them access to.
Requested resources are filtered based on the filter of the corresponding scope. For instance, if a service requests a user list (guarded with scope `read:users`) with a role that only contains scopes `read:users!user=hannah` and `read:users!user=ivan`, the returned list of user models will be an intersection of all users and the collection `{hannah, ivan}`. In case this intersection is empty, the API call returns an HTTP 404 error, regardless if any users exist outside of the clients scope filter collection.

In case a user resource is being accessed, any scopes with *group* filters will be expanded to filters for each *user* in those groups.

(vertical-filtering-target)=
## Vertical filtering

Vertical filtering, also called *attribute filtering*, is the concept of reducing the payload of an API call to cover only the *attributes* of the resources that the scopes of the client provides them access to. This occurs when the client scopes are subscopes of the API endpoint that is called.
For instance, if a client requests a user list with the only scope being `read:users:groups`, the returned list of user models will contain only a list of groups per user.
In case the client has multiple subscopes, the call returns the union of the data the client has access to.


The payload of an API call can be filtered both horizontally and vertically simultaneously. For instance, performing an API call to the endpoint `/users/` with the scope `users:name!user=juliette` returns a payload of `[{name: 'juliette'}]` (provided that this name is present in the database).
