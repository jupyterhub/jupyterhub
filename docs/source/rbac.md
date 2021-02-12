# JupyterHub RBAC

Role Based Access Control (RBAC) in JupyterHub serves to provide finer grained access to perform actions by users or services.

## Motivation
The JupyterHub API requires authentication before allowing changes to the administration system. For instance, currently the default behaviour is that creating or deleting users requires *admin rights*. This ensures that an arbitrary user, or even an unauthenticated third party, cannot disrupt the status of the Hub.

This system is functional, but lacks flexibility. If your Hub serves a number of users in different departments, you might want to delegate permissions to other users or automate certain processes. With this framework, appointing a 'group-only admin', or a bot that culls idle servers, requires granting full rights to all actions. This can be error-prone and violates the [principle of least privilige](https://en.wikipedia.org/wiki/Principle_of_least_privilege).

To remedy situations like this, we implement an RBAC system. By equipping users, groups and services with *roles* that supply them with a collection of permissions (*scopes*), administrators are able to fine-tune which parties are able to access which resources.

### Available scopes

[](./reference/rest-api.rst) documentation details all available scopes and which of these are required for what particular API request.

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
In the above example, `johan` has privileges inherited from class-A and class-B roles and the `teacher` role on top of those. Note the filters (`!group=`) limiting the priviliges only to the class-A and class-B group members. 

## Technical Implementation

```{admonition} Here's my title
:class: warning

Here's my admonition content
```
