# Summary of changes in JupyterHub

See `git log` for a more detailed summary.

## 0.5

- Single-user server must be run with Jupyter Notebook ≥ 4.0
- Require `--no-ssl` confirmation to allow the Hub to be run without SSL (e.g. behind SSL termination in nginx)


## 0.4

### 0.4.1

Fix removal of `/login` page in 0.4.0, breaking some OAuth providers.

### 0.4.0

- Add `Spawner.user_options_form` for specifying an HTML form to present to users,
  allowing users to influence the spawning of their own servers.
- Add `Authenticator.pre_spawn_start` and `Authenticator.post_spawn_stop` hooks,
  so that Authenticators can do setup or teardown (e.g. passing credentials to Spawner,
  mounting data sources, etc.).
  These methods are typically used with custom Authenticator+Spawner pairs.
- 0.4 will be the last JupyterHub release where single-user servers running IPython 3 is supported instead of Notebook ≥ 4.0.


## 0.3

- No longer make the user starting the Hub an admin
- start PAM sessions on login
- hooks for Authenticators to fire before spawners start and after they stop,
  allowing deeper interaction between Spawner/Authenticator pairs.
- login redirect fixes

## 0.2

- Based on standalone traitlets instead of IPython.utils.traitlets
- multiple users in admin panel
- Fixes for usernames that require escaping

## 0.1

First preview release

