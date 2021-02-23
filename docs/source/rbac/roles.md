# Roles
JupyterHub provides three **default roles** which are automatically loaded to the database at the startup:

```{admonition} **Default roles**
- **_user_** role carries single `all` scope that grants _least user access_ to perform only default user actions.
- **_admin_** role contains all available scopes and grants full rights to all actions similarly to the current admin status.
- **_server_** role allows for posting activity only through the single `users:activity` scope.
```

Roles can also be customly defined and assigned to users, services, groups and tokens. 

**_Users_** and **_services_** are assigned a default role ( **_user_** or **_admin_**)  if no custom role is requested based on their admin status.

**_Tokens_**’ roles cannot grant the token higher permissions than their owner’s roles. If no specific role is requested, tokens are assigned the default _user_ role. 

**_Groups_** do not require any role and are not assigned any roles by default. Once group roles are defined and assigned, the privileges of each group member are extended with the group roles in the background during the API request permission check. This is useful for requesting the same permissions for several users.

(define_role_target)=
## Defining Roles

### In `jupyterhub_config.py`

Roles can be defined or modified in the configuration file as a list of dictionaries. An example:
```python
c.JupyterHub.load_roles = [
 {
   'name': 'server-rights',
   'description': 'Allows parties to start and stop user servers',
   'scopes': ['users:servers', 'read:users:servers'],
   'users': ['alice', 'bob'],
   'services': ['idle-culler'],
   'groups': ['admin-group'],
   'tokens': ['foo-6f6e65','bar-74776f']
 }
]
```
The role `server-rights` now allows the starting and stopping of servers by any of the following:
- users `alice` and `bob`
- the service `idle-culler`
- any member of the `admin-group`
- requests using the tokens `foo-6f6e65` or `bar-74776f` (providing the tokens owner has at least the same permissions).

Another example:
```python
c.JupyterHub.load_roles.append({
 'description': 'Read-only user models',
 'name': 'reader',
 'scopes': ['read:users'],
 'services': ['external'],
 'users': ['maria', 'joe']
 }
)
```

The role `reader` allows users `maria` and `joe` and service `external` to read (but not modify) any user’s model.

```{admonition} Requirements
:class: warning
In a role definition, the `name` field is required, while all other fields are optional.
Moreover, `users`, `services`, `groups` and `tokens` only accept objects that already exist or are defined previously in the file.
It is not possible to implicitly add a new user to the database by defining a new role.
```

In case the role with a certain name already exists in the database, its definition and scopes will be overwritten. Any previously defined role bearers will remain unchanged, but newly defined requesters (in this case `maria` and `joe` and `external`) will be assigned the new role definition.
