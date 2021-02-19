# Technical Implementation

Roles are stored in the database similarly as users, services, etc., and can be added or modified as explained in {ref}`define_role_target`. Objects can gain, change and lose roles. For example, one can change a token's role, and as such its permissions, without the need to initiate new token (currently through `update_roles` and `remove_obj` functions in `roles.py`, this will be eventually available through APIs). Roles' and scopes' utilities can be found in `roles.py` and `scopes.py` modules.

## Resolving roles and scopes
Roles and scopes are resolved on several occasions, for example when requesting an API token with specific roles or making an API request. The following sections provide more details.  

### Requesting API token with specific roles
API tokens grant access to JupyterHub's APIs. The RBAC framework allows for requesting tokens with specific existing roles. To date, it is only possible to add roles to a token in two ways: 
1. through the `config.py` file as described in the {ref}`define_role_target` section 
2. through the POST /users/{name}/tokens API where the roles can be specified in the token parameters body (see [](../reference/rest-api.rst)).

The RBAC framework adds several steps into the token issue flow.

If no roles are requested, the token is issued with a default role (providing the requester is allowed to create the token).

If the token is requested with a specific role or multiple roles, the permissions of the would-be token's owner are checked against the requested permissions to ensure the token will not grant its owner additional privileges. In practice, this corresponds to resolving all the token owner's roles (including the roles associated with their groups) and the token's requested roles into a set of scopes. The two sets are compared and if the token's scopes are a subset of the token owner's scopes, the token is issued with the requested roles.

{ref}`Figure 1 <api-token-request-chart>` below illustrates this process. The orange rectangles highlight where in the process the roles and scopes are resolved.

```{figure} ../images/rbac-api-token-request-chart.png
:align: center
:name: api-token-request-chart

Figure 1. Resolving roles and scopes during API token request
```

```{note}
The above check is also performed when roles are requested for existing tokens, e.g., when adding tokens to {ref}`role definitions through the config.py <define_role_target>`.
```

### Making API request
With the RBAC framework each authenticated JupyterHub API request is guarded by a scope decorator that specifies which scopes are required to gain the access to the API. 

When an API request is performed, the passed API token's roles are again resolved into a set of scopes and compared to the scopes required to access the API as follows:
- if the API scopes are present within the set of token's scopes, the access is granted and the API returns its "full" response
- if that is not the case, another check is utilized to determine if sub-scopes of the required API scopes can be found in the token's scope set:
    - if the subscopes are present, the RBAC framework employs the {ref}`filtering <filtering-target>` procedures to refine the API response to provide access to only resource attributes specified by the token provided scopes
        - for example, providing a scope `read:users:activity!group=class-C` for the _GET /users_ API will return a list of user models from group `class-C` containing only the `last_activity` attribute for each user model
    - if the subscopes are not present, the access to API is denied    

{ref}`Figure 2 <api-request-chart>` illustrates this process highlighting the steps where the role and scope resolutions as well as filtering occur in orange.

```{figure} ../images/rbac-api-request-chart.png
:align: center
:name: api-request-chart

Figure 2. Resolving roles and scopes when an API request is made
```
