# Roles

JupyterHub provides four roles that are available by default:

```{admonition} **Default roles**
- `user` role provides a {ref}`default user scope <default-user-scope-target>` `self` that grants access to the user's own resources.
- `admin` role contains all available scopes and grants full rights to all actions. This role **cannot be edited**.
- `token` role provides a {ref}`default token scope <default-token-scope-target>` `all` that resolves to the same permissions as the owner of the token has.
- `server` role allows for posting activity of "itself" only.

**These roles cannot be deleted.**
```

The `user`, `admin`, and `token` roles by default all preserve the permissions prior to RBAC.
Only the `server` role is changed from pre-2.0, to reduce its permissions to activity-only
instead of the default of a full access token.

Additional custom roles can also be defined (see {ref}`define-role-target`).
Roles can be assigned to the following entities:

- Users
- Services
- Groups
- Tokens

An entity can have zero, one, or multiple roles, and there are no restrictions on which roles can be assigned to which entity. Roles can be added to or removed from entities at any time.

**Users** \
When a new user gets created, they are assigned their default role `user`. Additionaly, if the user is created with admin privileges (via `c.Authenticator.admin_users` in `jupyterhub_config.py` or `admin: true` via API), they will be also granted `admin` role. If existing user's admin status changes via API or `jupyterhub_config.py`, their default role will be updated accordingly (after next startup for the latter).

**Services** \
Services do not have a default role. Services without roles have no access to the guarded API end-points, so most services will require assignment of a role in order to function.

**Groups** \
A group does not require any role, and has no roles by default. If a user is a member of a group, they automatically inherit any of the group's permissions (see {ref}`resolving-roles-scopes-target` for more details). This is useful for assigning a set of common permissions to several users.

**Tokens** \
A token’s permissions are evaluated based on their owning entity. Since a token is always issued for a user or service, it can never have more permissions than its owner. If no specific role is requested for a new token, the token is assigned the `token` role.

(define-role-target)=

## Defining Roles

Roles can be defined or modified in the configuration file as a list of dictionaries. An example:

% TODO: think about loading users into roles if membership has been changed via API.
% What should be the result?

```python
# in jupyterhub_config.py

c.JupyterHub.load_roles = [
 {
   'name': 'server-rights',
   'description': 'Allows parties to start and stop user servers',
   'scopes': ['servers'],
   'users': ['alice', 'bob'],
   'services': ['idle-culler'],
   'groups': ['admin-group'],
 }
]
```

The role `server-rights` now allows the starting and stopping of servers by any of the following:

- users `alice` and `bob`
- the service `idle-culler`
- any member of the `admin-group`.

```{attention}
Tokens cannot be assigned roles through role definition but may be assigned specific roles when requested via API (see {ref}`requesting-api-token-target`).
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

`users`, `services`, and `groups` only accept objects that already exist in the database or are defined previously in the file.
It is not possible to implicitly add a new user to the database by defining a new role.
```

If no scopes are defined for _new role_, JupyterHub will raise a warning. Providing non-existing scopes will result in an error.

In case the role with a certain name already exists in the database, its definition and scopes will be overwritten. This holds true for all roles except the `admin` role, which cannot be overwritten; an error will be raised if trying to do so. All the role bearers permissions present in the definition will change accordingly.

(removing-roles-target)=

## Removing roles

Only the entities present in the role definition in the `jupyterhub_config.py` remain the role bearers. If a user, service or group is removed from the role definition, they will lose the role on the next startup.

Once a role is loaded, it remains in the database until removing it from the `jupyterhub_config.py` and restarting the Hub. All previously defined role bearers will lose the role and associated permissions. Default roles, even if previously redefined through the config file and removed, will not be deleted from the database.
