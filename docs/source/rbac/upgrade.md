The RBAC framework new in JupyterHub 2.0. enables for the different degrees of permissions to be granted to tokens via scopes tied to roles. This, no doubt eliminates the distinction between OAuth and API tokens as was been used in previous versions - (see {ref}`oauth-vs-api-tokens-target` to learn more). As a result, the different database setup in the previous JupyterHub versions are merged into one and as such, all tokens that already exist and were created prior to the upgrade must be replaced because they are no longer compatible with the updated database.

Here is how it works- During the database upgrade, all existing tokens are deleted and the tokens loaded via the `jupyterhub_config.py` file are recreated with updated structure. But following the upgrade, any manually created or saved tokens must be manually reissued because they are not automatically created.

**Please note that upgrading JupyterHub does not affect any database record**.

(rbac-upgrade-steps-target)=

## Upgrade steps

Let's take a look at the steps to follow when upgrading JupyterHub with RBAC framework.

Step1. Stop **all running servers** before proceeding with the upgrade.
Step2. To upgrade the Hub, follow the [Upgrading JupyterHub](../admin/upgrading.rst) instructions.

```{attention}
We advise against defining any new roles in the `jupyterhub.config.py` file right after the upgrade is completed and JupyterHub restarted for the first time. This preserves the 'current' state of the Hub. You can define and assign new roles on any other following startup.
```

Step3. After restarting the Hub from `step2 above` **re-issue all tokens that were previously issued manually** (i.e., not through the `jupyterhub_config.py` file).

**Note** When the JupyterHub is restarted for the first time after the upgrade, all users, services and tokens stored in the database or re-loaded through the configuration file will be assigned their default role. Any newly added entities after that will be assigned their default role only if no other specific role is requested for them.

## Changing the permissions after the upgrade

Once all the {ref}`upgrade steps <rbac-upgrade-steps-target>` above are completed, the RBAC framework will be available for utilization. You can define new roles, modify default roles (apart from `admin`) and assign them to entities as described in the {ref}`define-role-target` section.

To begin using RBAC, we advised the approach listed below:

1. Identify the admin users and services to which you want to assign the new roles, giving them access to only the rights they require
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

The RBAC framework allows for granting tokens different levels of permissions via scopes attached to roles. The 'only identify' purpose of the separate OAuth tokens is no longer required. API tokens can be used for every action, including the login and authentication, for which an API token with no role (i.e., no scope in {ref}`available-scopes-target`) is used.

OAuth tokens are therefore dropped from the Hub upgraded with the RBAC framework.
