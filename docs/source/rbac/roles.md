# Roles

JupyterHub provides four roles that are available by default:

```{admonition} **Default roles**
- `user` role provides a {ref}`default user scope <default-user-scope-target>` `self` that grants access to only the user's own resources.
- `admin` role contains all available scopes and grants full rights to all actions similarly to the current admin status. This role **cannot be edited**.
- `token` role provides a {ref}`default token scope <default-token-scope-target>` `all` that resolves to the same permissions as the token's owner has.
- `server` role allows for posting activity of "itself" only. The scope is currently under development.

**These roles cannot be deleted.**
```

New roles can also be customly defined (see {ref}`define_role_target`). Roles can be assigned to the following entities:

- Users
- Services
- Groups
- Tokens

An entity can have zero, one, or multiple roles, and there are no restrictions on which roles can be assigned to which entity. Roles can be added to or removed from entities at any time.

**Users and services** \
When a new user or service gets created, they are assigned their default role ( `user` or `admin`) if no custom role is requested, currently based on their admin status.

**Groups** \
A group does not require any role, and has no roles by default. If a user is a member of a group, they autimatically inherit any of the group's permissions (see {ref}`resolving-roles-scopes-target` for more details). This is useful for assigning a set of common permissions to several users.

**Tokens** \
A token’s permissions are evaluated based on their owning entity. Since a token is always issued for a user or service, it can never have more permissions than its owner. If no specific role is requested for a new token, the token is assigned the `token` role.

(define_role_target)=

## Defining Roles

Roles can be defined or modified in the configuration file as a list of dictionaries. An example:

```python
# in jupyterhub_config.py

c.JupyterHub.load_roles = [
 {
   'name': 'server-rights',
   'description': 'Allows parties to start and stop user servers',
   'scopes': ['users:servers'],
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

```{attention}
The `foo-6f6e65` and `bar-74776f` tokens will be assigned the `server-rights` role only if their owner has the corresponding permissions, otherwise JupyterHub throws an error. See {ref}`resolving-roles-scopes-target` for more details on how this is assessed.
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
In a role definition, the `name` field is required, while all other fields are optional.\
**Role names must:**
- be 3 - 255 characters
- use ascii lowercase, numbers, 'unreserved' URL punctuation `-_.~`
- start with a letter
- end with letter or number.

If no scopes are defined for new role, JupyterHub will raise a warning. Providing non-existing scopes will result in an error.\
Moreover, `users`, `services`, `groups` and `tokens` only accept objects that already exist or are defined previously in the file.\
It is not possible to implicitly add a new user to the database by defining a new role.
```

\
In case the role with a certain name already exists in the database, its definition and scopes will be overwritten. This holds true for all roles except the `admin` role, which cannot be overwritten; an error will be raised if trying to do so. \
Any previously defined role bearers for this role will remain the role bearers but their permissions will change if the role's permissions are overwritten. The newly defined bearers (in this case `maria` and `joe` and `external`) will be added to the existing ones.

Once a role is loaded, it remains in the database until explicitly deleting it through `delete_role()` function in `roles.py`. Default roles cannot be deleted. \
Omitting the `c.JupyterHub.load_roles` or specifying different roles in the `jupyterhub_config.py` file on the next startup will not erase previously defined roles, nor their bearers.
