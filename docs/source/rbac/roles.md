# Roles
JupyterHub provides three **default roles** which are automatically loaded to the database at the startup:

```{admonition} **Default roles**
- `user` role provides a {ref}`default user scope <default-user-scope-target>` `all` that grants access to only the user's own resources.
- `admin` role contains all available scopes and grants full rights to all actions similarly to the current admin status.
- `server` role allows for posting activity only through the single `users:activity` scope.
```

Roles can also be customly defined and assigned to users, services, groups and tokens. 

**_Users_** and **_services_** are assigned a default role ( `user` or `admin`)  if no custom role is requested based on their admin status.

**_Tokens_**’ roles cannot grant the token higher permissions than their owner’s roles. If no specific role is requested, tokens are assigned the `user` role. 

**_Groups_** do not require any role and are not assigned any roles by default. Once roles are defined and assigned to groups, the privileges of each group member are extended when needed (see {ref}`resolving-roles-scopes-target` for more details). This is useful for assigning a set of common permissions to several users.

(define_role_target)=
## Defining Roles

Roles can be defined or modified in the configuration file as a list of dictionaries. An example:
```python
# in jupyterhub_config.py

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
- requests using the tokens `foo-6f6e65` or `bar-74776f`.
```{note}
The `foo-6f6e65` and `bar-74776f` tokens will be assigned the `server-rights` role only if their owner has the same or higher permissions. For example, if the tokens' owner has only `user` role, JupyterHub will throw an error. See {ref}`Figure 1 <api-token-request-chart>` for more details.
```

Another example:
```python
# in jupyterhub_config.py

c.JupyterHub.load_roles = [
 {
   'description': 'Read-only user models',
   'name': 'reader',
   'scopes': ['read:users'],
   'services': ['external'],
   'users': ['maria', 'joe']
 }
]
```

The role `reader` allows users `maria` and `joe` and service `external` to read (but not modify) any user’s model.

```{admonition} Requirements
:class: warning
In a role definition, the `name` field is required, while all other fields are optional. If no scopes are defined for new role, JupyterHub will raise a warning.
Moreover, `users`, `services`, `groups` and `tokens` only accept objects that already exist or are defined previously in the file.
It is not possible to implicitly add a new user to the database by defining a new role.
```

In case the role with a certain name already exists in the database, its definition and scopes will be overwritten. This holds true for any role apart from `admin` role that cannot be overwritten; an error will be raised if trying to do so.
Any previously defined role bearers will remain unchanged, but newly defined requesters (in this case `maria` and `joe` and `external`) will be assigned the new role definition.

Once a role is loaded, it remains in the database until explicitly deleting it through `remove_role` function in `roles.py`. I.e., omitting the `c.JupyterHub.load_roles` or specifying different roles in the `jupyterhub_config.py` file on the next startup will not erase previously defined roles.
