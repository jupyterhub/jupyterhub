# Technical Implementation

Roles are stored in the database similarly as users, services, etc., and can be added or modified as explained in {ref}`define_role_target`. Objects can gain, change and lose roles. For example, one can change a token's role, and as such its permissions, without the need to initiate new token (currently through `add_obj` and `remove_obj` functions in `roles.py`, this will be eventually available through APIs). Roles' and scopes' utilities can be found in `roles.py` and `scopes.py` modules.

## Resolving roles and scopes
Roles and scopes are resolved on several occasions as shown in the {ref}`diagram below <checkpoint-fig>`.

```{figure} ../images/role-scope-resolution.png
:align: center
:name: checkpoint-fig

Figure 1. Checkpoints for resolving scopes in JupyterHub
```

### Checkpoint 1: Requesting a token with specific roles
When a token is requested with a specific role or multiple roles, the permissions of the token's owner (client in {ref}`Figure 1 <checkpoint-fig>`) are checked against the requested permissions to ensure the token will not grant its owner additional privileges. In practice, this corresponds to resolving all the client's roles (including the roles associated with their groups) and the token's requested roles into a set of scopes. The two sets are compared and if the token's scopes (s5 in {ref}`Figure 1 <checkpoint-fig>`) are a subset of the client's scopes, the token is issued with the requested roles (role D in {ref}`Figure 1 <checkpoint-fig>`).

```{note}
The above check is also performed when roles are requested for existing tokens, e.g., when adding tokens to {ref}`role definitions through the config.py <define_role_target>`.
```
### Checkpoint 2: Making an API request
Each authenticated API request is guarded by a scope decorator that specifies which scopes are required to gain the access to the API (scopes s1, s5 and s6 in {ref}`Figure 1 <checkpoint-fig>`). 

When an API request is performed, the token's roles are again resolved into a set of scopes and compared to the required scopes in the same way as in checkpoint 1. The access to the API is then either allowed or denied.

For instance, a token with a role with `groups!group=class-C` scope will be allowed to access the _GET /groups_ API but not allowed to make the _POST /groups/{name}_ API request.  

### Checkpoint 3: API request response
The third checkpoint takes place at the API response level. The scopes provided for the request (s5 in {ref}`Figure 1 <checkpoint-fig>`) are used to filter through the API response to provide access to only resource attributes specified by the scopes. 

For example, providing a scope `read:users:activity!group=class-C` for the _GET /users_ API will return a list of user models from group `class-C` containing only the last_activity attribute.

For more filtering details refer to the {ref}`filtering<filtering-target>` section.
