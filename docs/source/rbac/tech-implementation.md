# Technical Implementation

[Roles](roles) are stored in the database, where they are associated with users, services, and groups. Roles can be added or modified as explained in the {ref}`define-role-target` section. Users, services, groups, and tokens can gain, change, and lose roles. This is currently achieved via `jupyterhub_config.py` (see {ref}`define-role-target`) and will be made available via API in the future. The latter will allow for changing a user's role, and thereby its permissions, without the need to restart JupyterHub.

Roles and scopes utilities can be found in `roles.py` and `scopes.py` modules. Scope variables take on five different formats that are reflected throughout the utilities via specific nomenclature:

```{admonition} **Scope variable nomenclature**
:class: tip
- _scopes_ \
  List of scopes that may contain abbreviations (used in role definitions). E.g., `["users:activity!user", "self"]`.
- _expanded scopes_ \
  Set of fully expanded scopes without abbreviations (i.e., resolved metascopes, filters, and subscopes). E.g., `{"users:activity!user=charlie", "read:users:activity!user=charlie"}`.
- _parsed scopes_ \
  Dictionary representation of expanded scopes. E.g., `{"users:activity": {"user": ["charlie"]}, "read:users:activity": {"users": ["charlie"]}}`.
- _intersection_ \
  Set of expanded scopes as intersection of 2 expanded scope sets.
- _identify scopes_ \
  Set of expanded scopes needed for identity (whoami) endpoints.
```

(resolving-roles-scopes-target)=

## Resolving roles and scopes

**Resolving roles** involves determining which roles a user, service, or group has, extracting the list of scopes from each role and combining them into a single set of scopes.

**Resolving scopes** involves expanding scopes into all their possible subscopes (_expanded scopes_), parsing them into the format used for access evaluation (_parsed scopes_) and, if applicable, comparing two sets of scopes (_intersection_). All procedures take into account the scope hierarchy, {ref}`vertical <vertical-filtering-target>` and {ref}`horizontal filtering <horizontal-filtering-target>`, limiting or elevated permissions (`read:<resource>` or `admin:<resource>`, respectively), and metascopes.

Roles and scopes are resolved on several occasions, for example when requesting an API token with specific scopes or when making an API request. The following sections provide more details.

(requesting-api-token-target)=

### Requesting API token with specific scopes

:::{versionchanged} 3.0
API tokens have _scopes_ instead of roles,
so that their permissions cannot be updated.

You may still request roles for a token,
but those roles will be evaluated to the corresponding _scopes_ immediately.

Prior to 3.0, tokens stored _roles_,
which meant their scopes were resolved on each request.
:::

API tokens grant access to JupyterHub's APIs. The [RBAC framework](./index.md) allows for requesting tokens with specific permissions.

RBAC is involved in several stages of the OAuth token flow.

When requesting a token via the tokens API (`/users/:name/tokens`), or the token page (`/hub/token`),
if no scopes are requested, the token is issued with the permissions stored on the default `token` role
(provided the requester is allowed to create the token).

OAuth tokens are also requested via OAuth flow

If the token is requested with any scopes, the permissions of requesting entity are checked against the requested permissions to ensure the token would not grant its owner additional privileges.

If a token has any scopes that its owner does not possess
at the time of making the API request, those scopes are removed.
The API request is resolved without additional errors using the scope _intersection_;
the Hub logs a warning in this case (see {ref}`Figure 2 <api-request-chart>`).

Resolving a token's scope (yellow box in {ref}`Figure 1 <token-request-chart>`) corresponds to resolving all the roles of the token's owner (including the roles associated with their groups) and the token's own scopes into a set of scopes. The two sets are compared (Resolve the scopes box in orange in {ref}`Figure 1 <token-request-chart>`), taking into account the scope hierarchy.
If the token's scopes are a subset of the token owner's scopes, the token is issued with the requested scopes; if not, JupyterHub will raise an error.

{ref}`Figure 1 <token-request-chart>` below illustrates the steps involved. The orange rectangles highlight where in the process the roles and scopes are resolved.

```{figure} /images/rbac-token-request-chart.png
:align: center
:name: token-request-chart

Figure 1. Resolving roles and scopes during API token request
```

### Making an API request

With the RBAC framework, each authenticated JupyterHub API request is guarded by a scope decorator that specifies which scopes are required in order to gain the access to the API.

When an API request is made, the requesting API token's scopes are again intersected with its owner's (yellow box in {ref}`Figure 2 <api-request-chart>`) to ensure that the token does not grant more permissions than its owner has at the request time (e.g., due to changing/losing roles).
If the owner's roles do not include some scopes of the token, only the _intersection_ of the token's and owner's scopes will be used. For example, using a token with scope `users` whose owner's role scope is `read:users:name` will result in only the `read:users:name` scope being passed on. In the case of no _intersection_, an empty set of scopes will be used.

The passed scopes are compared to the scopes required to access the API as follows:

- if the API scopes are present within the set of passed scopes, the access is granted and the API returns its "full" response

- if that is not the case, another check is utilized to determine if subscopes of the required API scopes can be found in the passed scope set:

  - if found, the RBAC framework employs the {ref}`filtering <vertical-filtering-target>` procedures to refine the API response to access only resource attributes corresponding to the passed scopes. For example, providing a scope `read:users:activity!group=class-C` for the `GET /users` API will return a list of user models from group `class-C` containing only the `last_activity` attribute for each user model

  - if not found, the access to API is denied

{ref}`Figure 2 <api-request-chart>` illustrates this process highlighting the steps where the role and scope resolutions as well as filtering occur in orange.

```{figure} /images/rbac-api-request-chart.png
:align: center
:name: api-request-chart

Figure 2. Resolving roles and scopes when an API request is made
```
