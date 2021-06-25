# Upgrading JupyterHub with RBAC framework

RBAC framework requires different database setup than any previous JupyterHub versions due to eliminating the distinction between OAuth and API tokens (see {ref}`oauth-vs-api-tokens-target` for more details). This requires merging the previously two different database tables into one. By doing so, all existing tokens created before the upgrade no longer comply with the new database version and must be replaced.

This is achieved by the Hub deleting all existing tokens during the database upgrade and recreating the tokens loaded via the `jupyterhub_config.py` file with updated structure. However, any manually issued or stored tokens are not recreated automatically and must be manually re-issued after the upgrade.

No other database records are affected.

(rbac-upgrade-steps-target)=

## Upgrade steps

1. All running **servers must be stopped** before proceeding with the upgrade.
2. To upgrade the Hub, follow the [Upgrading JupyterHub](../admin/upgrading.rst) instructions.
   ```{attention}
   We advise against defining any new roles in the `jupyterhub.config.py` file right after the upgrade is completed and JupyterHub restarted for the first time. This preserves the 'current' state of the Hub. You can define and assign new roles on any other following startup.
   ```
3. After restarting the Hub **re-issue all tokens that were previously issued manually** (i.e., not through the `jupyterhub_config.py` file).

When the JupyterHub is restarted for the first time after the upgrade, all users, services and tokens stored in the database or re-loaded through the configuration file will be assigned their default role. Any newly added entities after that will be assigned their default role only if no other specific role is requested for them.

## Changing the permissions after the upgrade

Once all the {ref}`upgrade steps <rbac-upgrade-steps-target>` above are completed, the RBAC framework will be available for utilization. You can define new roles, modify default roles (apart from `admin`) and assign them to entities as described in the {ref}`define-role-target` section.

We recommended the following procedure to start with RBAC:

1. Identify which admin users and services you would like to grant only the permissions they need through the new roles.
2. Strip these users and services of their admin status via API or UI. This will change their roles from `admin` to `user`.
   ```{note}
   Stripping entities of their roles is currently available only via `jupyterhub_config.py` (see {ref}`removing-roles-target`).
   ```
3. Define new roles that you would like to start using with appropriate scopes and assign them to these entities in `jupyterhub_config.py`.
4. Restart the JupyterHub for the new roles to take effect.

(oauth-vs-api-tokens-target)=

## OAuth vs API tokens

### Before RBAC

Previous JupyterHub versions utilize two types of tokens, OAuth token and API token.

OAuth token is issued by the Hub to a single-user server when the user logs in. The token is stored in the browser cookie and is used to identify the user who owns the server during the OAuth flow. This token by default expires when the cookie reaches its expiry time of 2 weeks (or after 1 hour in JupyterHub versions < 1.3.0).

API token is issued by the Hub to a single-user server when launched and is used to communicate with the Hub's APIs such as posting activity or completing the OAuth flow. This token has no expiry by default.

API tokens can also be issued to users via API ([_/hub/token_](../reference/urls.md) or [_POST /users/:username/tokens_](../reference/rest-api.rst)) and services via `jupyterhub_config.py` to perform API requests.

### With RBAC

The RBAC framework allows for granting tokens different levels of permissions via scopes attached to roles. The 'only identify' purpose of the separate OAuth tokens is no longer required. API tokens can be used used for every action, including the login and authentication, for which an API token with no role (i.e., no scope in {ref}`available-scopes-target`) is used.

OAuth tokens are therefore dropped from the Hub upgraded with the RBAC framework.
