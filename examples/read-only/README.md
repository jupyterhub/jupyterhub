# Granting read-only access to user servers

Jupyter Server 2.0 adds the ability to enforce granular permissions via its Authorizer API.
Combining this with JupyterHub's custom scopes and singleuser-server extension, you can use JupyterHub to grant users restricted (e.g. read-only) access to each others' servers,
rather than an all-or-nothing access permission.

This example demonstrates granting read-only access to just one specific user's server to one specific other user,
but you can grant access for groups, all users, etc.
Given users `vex` and `percy`, we want `vex` to have permission to:

1. read and open files, and view the state of the server, but
2. not write or edit files
3. not start/stop the server
4. not execute anything

(Jupyter Server's Authorizer API allows for even more fine-grained control)

To test this, you'll want two browser sessions:

1. login as `percy` (dummy auth means username and no password needed) and start the server
2. in another session (another browser, or logout as percy), login as `vex` (again, any password in the example)
3. as vex, visit http://127.0.0.1:8000/users/percy/

Percy can use their server as normal, but vex will only be able to read files.
Vex won't be able to run any code, connect to kernels, or save edits to files.

Note that defining custom scopes does not enforce that they are used.
Defining scopes for read-only access and then running user servers without the custom Authorizer
will result in users who are supposed to have read-only access actually having unrestricted access,
because only the default `access:servers` scope is checked.
