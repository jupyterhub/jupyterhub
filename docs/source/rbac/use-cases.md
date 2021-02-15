# Use Cases

To determine which scopes a role should have it is best to follow these steps:
1. Determine what actions the role holder should have/have not access to
2. Match the actions against the JupyterHub's REST APIs
3. Check which scopes are required to access the APIs
4. Define the role with required scopes and assign to users/services/groups/tokens

Below, different use cases are presented on how to use the RBAC framework.

## User scripting their own access

A regular user should be able to view and manage all of their own resources. This can be achieved using the scope `all` (or assigning the default _user_ role). If the user's access is to be restricted from modifying any of their resources (e.g., during marking), their role should be changed to read-only access, in this case scope `read:all`.
  
## Service to cull idle servers

Finding and shutting down idle servers can save a lot of computational resources.
Below follows a short tutorial on how one can add a cull-idle service to JupyterHub.

1. Request an API token
2. Define the service (`idle-culler`)
3. Define the role (scopes `users:servers`, `admin:users:servers`)
4. Install cull-idle servers (`pip install jupyterhub-idle-culler`)
5. Add the service to `jupyterhub_config.py`
6. (Restart JupyterHub)


## API launcher
A service capable of creating/removing users and launching multiple servers should have access to:
1. POST and DELETE /users
2. POST and DELETE /users/{name}/server
3. Creating/deleting servers

From the above, the scopes required for the role are
1. `admin:users`
2. `users:servers`
3. `admin:users:servers`

If needed, the scopes can be modified to limit the associated permissions to e.g. a particular group members with `!group=groupname` filter.

## Users as group admins/Group admin roles

Roles can be used to specify different group member privileges.

For example, a group of students `class-A` may have a role allowing all group members to access information about their group. Teacher `johan`, who is a member of `class-A` and a member of another group of students `class-B`, can have additional role permitting him access information about his group members as well as start/stop their servers.

The roles can then be defined as follows:
```python
c.JupyterHub.load_groups = {
    'class-A': ['johan', 'student1', 'student2'],
    'class-B': ['johan', 'student3', 'student4']
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
   'scopes': ['read:users!group=class-A', 'read:users!group=class-B', 'users:servers!group=class-A', 'users:servers!group=class-B'],
   'users': ['johan']
 }
]
``` 
In the above example, `johan` has privileges inherited from class-A and class-B roles and the `teacher` role on top of those. 
**Note the filters (`!group=`) limiting the priviliges only to the `class-A` and `class-B` group members.** 
