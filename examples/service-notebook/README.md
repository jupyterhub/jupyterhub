# Running a shared notebook as a service

This directory contains two examples of running a shared notebook server as a service,
one as a 'managed' service, and one as an external service with supervisor.

These examples require jupyterhub >= 0.7.2.

A single-user notebook server is run as a service,
and uses groups to authenticate a collection of users with the Hub.

In these examples, a JupyterHub group `'shared'` is created,
and a notebook server is spawned at `/services/shared-notebook`.
Any user in the `'shared'` group will be able to access the notebook server at `/services/shared-notebook/`.

In both examples, you will want to select the name of the group,
and the name of the shared-notebook service.

In the external example, some extra steps are required to set up supervisor:

1. select a system user to run the service. This is  a user on the system, and does not need to be a Hub user. Add this to the user field in `shared-notebook.conf`, replacing `someuser`.
2. generate a secret token for authentication, and replace the `super-secret` fields in `shared-notebook-service` and `jupyterhub_config.py`
3. install `shared-notebook-service` somewhere on your system, and update `/path/to/shared-notebook-service` to the absolute path of this destination
3. copy `shared-notebook.conf` to `/etc/supervisor/conf.d/`
4. `supervisorctl reload`
