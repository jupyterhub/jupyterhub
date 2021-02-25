# Use Cases

To determine which scopes a role should have it is best to follow these steps:
1. Determine what actions the role holder should have/have not access to
2. Match the actions against the JupyterHub's REST APIs
3. Check which scopes are required to access the APIs
4. Customize the scopes with filters if needed
5. Define the role with required scopes and assign to users/services/groups/tokens

Below, different use cases are presented on how to use the RBAC framework.

## User access

A regular user should be able to view and manage all of their own resources. This can be achieved using the scope `all` (or assigning the `user` role). If the user's access is to be restricted from modifying any of their resources (e.g., when a teacher wants to check their notebooks), their role should be changed to read-only access, in this case scope `read:all`.
  
## Service to cull idle servers

Finding and shutting down idle servers can save a lot of computational resources.
We can make use of [jupyterhub-idle-culler](https://github.com/jupyterhub/jupyterhub-idle-culler) to manage this for us.
Below follows a short tutorial on how to add a cull-idle service in the RBAC system.

1. Install the cull-idle server script with `pip install jupyterhub-idle-culler`.
2. Define a new service `idle-culler` and a new role for this service:
    ```python
    # in jupyterhub_config.py

    c.JupyterHub.services = [
        {
            "name": "idle-culler",
            "command": [
                sys.executable, "-m",
                "jupyterhub_idle_culler", 
                "--timeout=3600"
            ],
        }
    ]

    c.JupyterHub.load_roles = [
        {
            "name": "idle-culler",
            "description": "Culls idle servers",
            "scopes": ["read:users:name", "read:users:activity", "read:users:servers", "users:servers"],
            "services": ["idle-culler"],
        }
    ]
    ```
    ```{important}
    Note that in the RBAC system the `admin` field in the `idle-culler` service definition is omitted. Instead, the `idle-culler` role provides the service with only the permissions it needs.

    If the optional actions of deleting the idle servers and/or removing inactive users are desired, **add the following scopes** to the `idle-culler` role definition:
    - `admin:users:servers` for deleting servers
    - `admin:users` for deleting users.
    ```
3. Restart JupyterHub to complete the process.


## API launcher
A service capable of creating/removing users and launching multiple servers should have access to:
1. POST and DELETE /users
2. POST and DELETE /users/{name}/server
3. Creating/deleting servers

From the above, the scopes required for the role are
1. `admin:users`
2. `users:servers`
3. `admin:users:servers`

If needed, the scopes can be modified to limit the permissions to e.g. a particular group with `!group=groupname` filter.

## Users as group admins/Group admin roles

Roles can be used to specify different group member privileges.

For example, a group of students `class-A` may have a role allowing all group members to access information about their group. Teacher `johan`, who is a student of `class-A` but a teacher of another group of students `class-B`, can have additional role permitting him to access information about `class-B` students as well as start/stop their servers.

The roles can then be defined as follows:
```python
# in jupyterhub_config.py

c.JupyterHub.load_groups = {
    'class-A': ['johan', 'student1', 'student2'],
    'class-B': ['student3', 'student4']
}

c.JupyterHub.load_roles = [
    {
        'name': 'class-A-student',
        'description': 'Grants access to information about the group',
        'scopes': ['read:groups!group=class-A'],
        'groups': ['class-A']
    },
    {
        'name': 'class-B-student',
        'description': 'Grants access to information about the group',
        'scopes': ['read:groups!group=class-B'],
        'groups': ['class-B']
    },
    {
        'name': 'teacher',
        'description': 'Allows for accessing information about teacher group members and starting/stopping their servers',
        'scopes': [ 'read:users!group=class-B', 'users:servers!group=class-B'],
        'users': ['johan']
    }
]
``` 
In the above example, `johan` has privileges inherited from `class-A-student` role and the `teacher` role on top of those. 
```{note}
The scope filters (`!group=`) limit the privileges only to the particular groups. `johan` can access the servers and information of `class-B` group members only.
```
