# JupyterHub RBAC

Role Based Access Control (RBAC) in JupyterHub serves to provide finer grained access to perform actions by users or services.

## Motivation
The JupyterHub API requires authentication before allowing changes to the administration system. For instance, currently the default behaviour is that creating or deleting users requires *admin rights*. This ensures that an arbitrary user, or even an unauthenticated third party, cannot disrupt the status of the Hub.

This system is functional, but lacks flexibility. If your Hub serves a number of users in different departments, you might want to delegate permissions to other users or automate certain processes. With this framework, appointing a 'group-only admin', or a bot that culls idle servers, requires granting full rights to all actions. This can be error-prone and violates the [principle of least privilige](https://en.wikipedia.org/wiki/Principle_of_least_privilege).

To remedy situations like this, we implement an RBAC system. By equipping users, groups and services with *roles* that supply them with a collection of permissions (*scopes*), administrators are able to fine-tune which parties are able to access which resources.

## Definitions
__Scopes__ are specific permissions used to evaluate API requests. For example: the API endpoint `users/servers`, which enables starting or stopping user servers, is guarded by the scope `users:servers`.

Scopes are not directly assigned to requesters. Rather, when a client performs an API call, their access will be evaluated based on their assigned roles.

__Roles__ are collections of scopes that specify the level of what a client is allowed to do. For example, a group administrator may be granted permission to control the servers of group members, but not to create, modify or delete group members themselves.
Within the RBAC framework, this is achieved by assigning a role to the administrator that covers exactly those privileges.

## Technical Overview

```{toctree}
:maxdepth: 2

roles
scopes
use-cases
tech-implementation
```
