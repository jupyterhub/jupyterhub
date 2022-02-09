# JupyterHub RBAC

Role Based Access Control (RBAC) in JupyterHub serves to provide fine grained control of access to Jupyterhub's API resources.

RBAC is new in JupyterHub 2.0.

## Motivation

The JupyterHub API requires authorization to access its APIs.
This ensures that an arbitrary user, or even an unauthenticated third party, are not allowed to perform such actions.
For instance, the behaviour prior to adoption of RBAC is that creating or deleting users requires _admin rights_.

The prior system is functional, but lacks flexibility. If your Hub serves a number of users in different groups, you might want to delegate permissions to other users or automate certain processes.
Prior to RBAC, appointing a 'group-only admin' or a bot that culls idle servers, requires granting full admin rights to all actions. This poses a risk of the user or service intentionally or unintentionally accessing and modifying any data within the Hub and violates the [principle of least privilege](https://en.wikipedia.org/wiki/Principle_of_least_privilege).

To remedy situations like this, JupyterHub is transitioning to an RBAC system. By equipping users, groups and services with _roles_ that supply them with a collection of permissions (_scopes_), administrators are able to fine-tune which parties are granted access to which resources.

## Definitions

**Scopes** are specific permissions used to evaluate API requests. For example: the API endpoint `users/servers`, which enables starting or stopping user servers, is guarded by the scope `servers`.

Scopes are not directly assigned to requesters. Rather, when a client performs an API call, their access will be evaluated based on their assigned roles.

**Roles** are collections of scopes that specify the level of what a client is allowed to do. For example, a group administrator may be granted permission to control the servers of group members, but not to create, modify or delete group members themselves.
Within the RBAC framework, this is achieved by assigning a role to the administrator that covers exactly those privileges.

## Technical Overview

```{toctree}
:maxdepth: 2

roles
scopes
use-cases
tech-implementation
upgrade
```
