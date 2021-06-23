# Technical Implementation

Roles are stored in the database, where they are associated with users, services, etc., and can be added or modified as explained in {ref}`define-role-target` section. Users, services, groups, and tokens can gain, change, and lose roles. This is currently achieved via `jupyterhub_config.py` (see {ref}`define-role-target`) and will be made available via API in future. The latter will allow for changing a token's role, and thereby its permissions, without the need to issue a new token.

Roles and scopes utilities can be found in `roles.py` and `scopes.py` modules. Scope variables take on five different formats which is reflected throughout the utilities via specific nomenclature:

```{admonition} **Scope variable nomenclature**
:class: tip
- _scopes_ \
  List of scopes with abbreviations (used in role definitions). E.g., `["users:activity!user"]`.
- _expanded scopes_ \
  Set of expanded scopes without abbreviations (i.e., resolved metascopes, filters and subscopes). E.g., `{"users:activity!user=charlie", "read:users:activity!user=charlie"}`.
- _parsed scopes_ \
  Dictionary JSON like format of expanded scopes. E.g., `{"users:activity": {"user": ["charlie"]}, "read:users:activity": {"users": ["charlie"]}}`.
- _intersection_ \
  Set of expanded scopes as intersection of 2 expanded scope sets.
- _identify scopes_ \
  Set of expanded scopes needed for identify (whoami) endpoints.
```

(resolving-roles-scopes-target)=

## Resolving roles and scopes

**Resolving roles** refers to determining which roles a user, service, token, or group has, extracting the list of scopes from each role and combining them into a single set of scopes.

**Resolving scopes** involves expanding scopes into all their possible subscopes (_expanded scopes_), parsing them into format used for access evaluation (_parsed scopes_) and, if applicable, comparing two sets of scopes (_intersection_). All procedures take into account the scope hierarchy, {ref}`vertical <vertical-filtering-target>` and {ref}`horizontal filtering <horizontal-filtering-target>`, limiting or elevated permissions (`read:<resource>` or `admin:<resource>`, respectively), and metascopes.

Roles and scopes are resolved on several occasions, for example when requesting an API token with specific roles or making an API request. The following sections provide more details.

(requesting-api-token-target)=

### Requesting API token with specific roles

API tokens grant access to JupyterHub's APIs. The RBAC framework allows for requesting tokens with specific existing roles. To date, it is only possible to add roles to a token through the _POST /users/:name/tokens_ API where the roles can be specified in the token parameters body (see [](../reference/rest-api.rst)).

RBAC adds several steps into the token issue flow.

If no roles are requested, the token is issued with the default `token` role (providing the requester is allowed to create the token).

If the token is requested with any roles, the permissions of requesting entity are checked against the requested permissions to ensure the token would not grant its owner additional privileges.

If, due to modifications of roles or entities, at API request time a token has any scopes that its owner does not, those scopes are removed. The API request is resolved without additional errors using the scopes _intersection_, but the Hub logs a warning (see {ref}`Figure 2 <api-request-chart>`).

Resolving a token's roles (yellow box in {ref}`Figure 1 <token-request-chart>`) corresponds to resolving all the token's owner roles (including the roles associated with their groups) and the token's requested roles into a set of scopes. The two sets are compared (Resolve the scopes box in orange in {ref}`Figure 1 <token-request-chart>`), taking into account the scope hierarchy but, solely for role assignment, omitting any {ref}`horizontal filter <horizontal-filtering-target>` comparison. If the token's scopes are a subset of the token owner's scopes, the token is issued with the requested roles; if not, JupyterHub will raise an error.

{ref}`Figure 1 <token-request-chart>` below illustrates the steps involved. The orange rectangles highlight where in the process the roles and scopes are resolved.

```{figure} ../images/rbac-token-request-chart.png
:align: center
:name: token-request-chart

Figure 1. Resolving roles and scopes during API token request
```

### Making an API request

With the RBAC framework each authenticated JupyterHub API request is guarded by a scope decorator that specifies which scopes are required to gain the access to the API.

When an API request is performed, the requesting API token's roles are again resolved (yellow box in {ref}`Figure 2 <api-request-chart>`) to ensure the token does not grant more permissions than its owner has at the request time (e.g., due to changing/losing roles).
If the owner's roles do not include some scopes of the token's scopes, only the _intersection_ of the token's and owner's scopes will be used. For example, using a token with scope `users` whose owner's role scope is `read:users:name` will result in only the `read:users:name` scope being passed on. In the case of no _intersection_, an empty set of scopes will be used.

The passed scopes are compared to the scopes required to access the API as follows:

- if the API scopes are present within the set of passed scopes, the access is granted and the API returns its "full" response

- if that is not the case, another check is utilized to determine if subscopes of the required API scopes can be found in the passed scope set:

  - if found, the RBAC framework employs the {ref}`filtering <vertical-filtering-target>` procedures to refine the API response to access only resource attributes corresponding to the passed scopes. For example, providing a scope `read:users:activity!group=class-C` for the _GET /users_ API will return a list of user models from group `class-C` containing only the `last_activity` attribute for each user model

  - if not found, the access to API is denied

{ref}`Figure 2 <api-request-chart>` illustrates this process highlighting the steps where the role and scope resolutions as well as filtering occur in orange.

```{figure} ../images/rbac-api-request-chart.png
:align: center
:name: api-request-chart

Figure 2. Resolving roles and scopes when an API request is made
```
