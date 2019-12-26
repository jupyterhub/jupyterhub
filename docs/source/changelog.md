# Changelog

For detailed changes from the prior release, click on the version number, and
its link will bring up a GitHub listing of changes. Use `git log` on the
command line for details.


## [Unreleased]

## 1.1

### [1.1.0b1] 2019-12-26

1.1 is a release with lots of accumulated fixes and improvements,
especially in performance, metrics, and customization.
There are no database changes in 1.1, so no database upgrade is required
when upgrading from 1.0 to 1.1.

Of particular interest to deployments with automatic health checking and/or large numbers of users is that the slow startup time
introduced in 1.0 by additional spawner validation can now be mitigated by `JupyterHub.init_spawners_timeout`,
allowing the Hub to become responsive before the spawners may have finished validating.

Several new Prometheus metrics are added (and others fixed!)
to measure sources of common performance issues,
such as proxy interactions and startup.

1.1 also begins adoption of the Jupyter telemetry project in JupyterHub,
See [The Jupyter Telemetry docs](https://jupyter-telemetry.readthedocs.io)
for more info. The only events so far are starting and stopping servers,
but more will be added in future releases.

There are many more fixes and improvements listed below.
Thanks to everyone who has contributed to this release!


#### New

- Add prometheus metric to measure hub startup time [#2799](https://github.com/jupyterhub/jupyterhub/pull/2799) ([@rajat404](https://github.com/rajat404))
- Add Spawner.auth_state_hook [#2555](https://github.com/jupyterhub/jupyterhub/pull/2555) ([@rcthomas](https://github.com/rcthomas))
- Link services from jupyterhub pages [#2763](https://github.com/jupyterhub/jupyterhub/pull/2763) ([@rcthomas](https://github.com/rcthomas))
- Add Spawner.auth_state_hook [#2555](https://github.com/jupyterhub/jupyterhub/pull/2555) ([@rcthomas](https://github.com/rcthomas))
- `JupyterHub.user_redirect_hook` is added to allow admins to customize /user-redirect/ behavior [#2790](https://github.com/jupyterhub/jupyterhub/pull/2790) ([@yuvipanda](https://github.com/yuvipanda))
- Add prometheus metric to measure hub startup time [#2799](https://github.com/jupyterhub/jupyterhub/pull/2799) ([@rajat404](https://github.com/rajat404))
- Add prometheus metric to measure proxy route poll times [#2798](https://github.com/jupyterhub/jupyterhub/pull/2798) ([@rajat404](https://github.com/rajat404))
- `PROXY_DELETE_DURATION_SECONDS` prometheus metric is added, to measure proxy route deletion times [#2788](https://github.com/jupyterhub/jupyterhub/pull/2788) ([@rajat404](https://github.com/rajat404))
- `Service.oauth_no_confirm` is added, it is useful for admin-managed services that are considered part of the Hub and shouldn't need to prompt the user for access [#2767](https://github.com/jupyterhub/jupyterhub/pull/2767) ([@minrk](https://github.com/minrk))
- `JupyterHub.default_server_name` is added to make the default server be a named server with provided name [#2735](https://github.com/jupyterhub/jupyterhub/pull/2735) ([@krinsman](https://github.com/krinsman))
- `JupyterHub.init_spawners_timeout` is introduced to combat slow startups on large JupyterHub deployments [#2721](https://github.com/jupyterhub/jupyterhub/pull/2721) ([@minrk](https://github.com/minrk))
- The configuration `uids` for local authenticators is added to consistently assign users UNIX id's between installations [#2687](https://github.com/jupyterhub/jupyterhub/pull/2687) ([@rgerkin](https://github.com/rgerkin))
- `JupyterHub.activity_resolution` is introduced with a default value of 30s improving performance by not updating the database with user activity too often [#2605](https://github.com/jupyterhub/jupyterhub/pull/2605) ([@minrk](https://github.com/minrk))
- [HubAuth](https://jupyterhub.readthedocs.io/en/stable/api/services.auth.html#jupyterhub.services.auth.HubAuth)'s SSL configuration can now be set through environment variables [#2588](https://github.com/jupyterhub/jupyterhub/pull/2588) ([@cmd-ntrf](https://github.com/cmd-ntrf))
- Expose spawner.user_options in REST API. [#2755](https://github.com/jupyterhub/jupyterhub/pull/2755) ([@danielballan](https://github.com/danielballan))
- add block for scripts included in head [#2828](https://github.com/jupyterhub/jupyterhub/pull/2828) ([@bitnik](https://github.com/bitnik))
- Instrument JupyterHub to record events with jupyter_telemetry [Part II] [#2698](https://github.com/jupyterhub/jupyterhub/pull/2698) ([@Zsailer](https://github.com/Zsailer))
- Make announcements visible without custom HTML [#2570](https://github.com/jupyterhub/jupyterhub/pull/2570) ([@consideRatio](https://github.com/consideRatio))
- Display server version on admin page [#2776](https://github.com/jupyterhub/jupyterhub/pull/2776) ([@vilhelmen](https://github.com/vilhelmen))

#### Fixes

- Cleanup if spawner stop fails [#2849](https://github.com/jupyterhub/jupyterhub/pull/2849) ([@gabber12](https://github.com/gabber12))
- Fix an issue occurring with the default spawner and `internal_ssl` enabled [#2785](https://github.com/jupyterhub/jupyterhub/pull/2785) ([@rpwagner](https://github.com/rpwagner))
- Fix named servers to not be spawnable unless activated [#2772](https://github.com/jupyterhub/jupyterhub/pull/2772) ([@bitnik](https://github.com/bitnik))
- JupyterHub now awaits proxy availability before accepting web requests [#2750](https://github.com/jupyterhub/jupyterhub/pull/2750) ([@minrk](https://github.com/minrk))
- Fix a no longer valid assumption that MySQL and MariaDB need to have `innodb_file_format` and `innodb_large_prefix` configured [#2712](https://github.com/jupyterhub/jupyterhub/pull/2712) ([@chicocvenancio](https://github.com/chicocvenancio))
- Login/Logout button now updates to Login on logout [#2705](https://github.com/jupyterhub/jupyterhub/pull/2705) ([@aar0nTw](https://github.com/aar0nTw))
- Fix handling of exceptions within `pre_spawn_start` hooks [#2684](https://github.com/jupyterhub/jupyterhub/pull/2684) ([@GeorgianaElena](https://github.com/GeorgianaElena))
- Fix an issue where a user could end up spawning a default server instead of a named server as intended [#2682](https://github.com/jupyterhub/jupyterhub/pull/2682) ([@rcthomas](https://github.com/rcthomas))
- /hub/admin now redirects to login if unauthenticated [#2670](https://github.com/jupyterhub/jupyterhub/pull/2670) ([@GeorgianaElena](https://github.com/GeorgianaElena))
- Fix spawning of users with names containing characters that needs to be escaped [#2648](https://github.com/jupyterhub/jupyterhub/pull/2648) ([@nicorikken](https://github.com/nicorikken))
- Fix `TOTAL_USERS` prometheus metric [#2637](https://github.com/jupyterhub/jupyterhub/pull/2637) ([@GeorgianaElena](https://github.com/GeorgianaElena))
- Fix `RUNNING_SERVERS` prometheus metric [#2629](https://github.com/jupyterhub/jupyterhub/pull/2629) ([@GeorgianaElena](https://github.com/GeorgianaElena))
- Fix faulty redirects to 404 that could occur with the use of named servers [#2594](https://github.com/jupyterhub/jupyterhub/pull/2594) ([@vilhelmen](https://github.com/vilhelmen))
- JupyterHub API spec is now a valid OpenAPI spec [#2590](https://github.com/jupyterhub/jupyterhub/pull/2590) ([@sbrunk](https://github.com/sbrunk))
- Use of `--help` or `--version` previously could output unrelated errors [#2584](https://github.com/jupyterhub/jupyterhub/pull/2584) ([@minrk](https://github.com/minrk))
- No longer crash on startup in Windows [#2560](https://github.com/jupyterhub/jupyterhub/pull/2560) ([@adelcast](https://github.com/adelcast))
- Escape usernames in the frontend [#2640](https://github.com/jupyterhub/jupyterhub/pull/2640) ([@nicorikken](https://github.com/nicorikken))

#### Maintenance

- chore: Dockerfile updates [#2853](https://github.com/jupyterhub/jupyterhub/pull/2853) ([@jgwerner](https://github.com/jgwerner))
- simplify Dockerfile [#2840](https://github.com/jupyterhub/jupyterhub/pull/2840) ([@minrk](https://github.com/minrk))
- docker: fix onbuild image arg [#2839](https://github.com/jupyterhub/jupyterhub/pull/2839) ([@minrk](https://github.com/minrk))
- remove redundant pip package list in docs environment.yml [#2838](https://github.com/jupyterhub/jupyterhub/pull/2838) ([@minrk](https://github.com/minrk))
- docs: Update docs to run tests [#2812](https://github.com/jupyterhub/jupyterhub/pull/2812) ([@jgwerner](https://github.com/jgwerner))
- remove redundant pip package list in docs environment.yml [#2838](https://github.com/jupyterhub/jupyterhub/pull/2838) ([@minrk](https://github.com/minrk))
- updating to pandas docs theme [#2820](https://github.com/jupyterhub/jupyterhub/pull/2820) ([@choldgraf](https://github.com/choldgraf))
- Adding institutional faq [#2800](https://github.com/jupyterhub/jupyterhub/pull/2800) ([@choldgraf](https://github.com/choldgraf))
- Add inline comment to test [#2826](https://github.com/jupyterhub/jupyterhub/pull/2826) ([@consideRatio](https://github.com/consideRatio))
- Raise error on missing specified config [#2824](https://github.com/jupyterhub/jupyterhub/pull/2824) ([@consideRatio](https://github.com/consideRatio))
- chore: Refactor Dockerfile [#2816](https://github.com/jupyterhub/jupyterhub/pull/2816) ([@jgwerner](https://github.com/jgwerner))
- chore: Update python versions in travis matrix [#2811](https://github.com/jupyterhub/jupyterhub/pull/2811) ([@jgwerner](https://github.com/jgwerner))
- chore: Bump package versions used in pre-commit config [#2810](https://github.com/jupyterhub/jupyterhub/pull/2810) ([@jgwerner](https://github.com/jgwerner))
- adding docs preview to circleci [#2803](https://github.com/jupyterhub/jupyterhub/pull/2803) ([@choldgraf](https://github.com/choldgraf))
- adding institutional faq [#2800](https://github.com/jupyterhub/jupyterhub/pull/2800) ([@choldgraf](https://github.com/choldgraf))
- The proxy's REST API listens on port `8001` [#2795](https://github.com/jupyterhub/jupyterhub/pull/2795) ([@bnuhero](https://github.com/bnuhero))
- cull_idle_servers.py: rebind max_age and inactive_limit locally [#2794](https://github.com/jupyterhub/jupyterhub/pull/2794) ([@rkdarst](https://github.com/rkdarst))
- Fix deprecation warnings [#2789](https://github.com/jupyterhub/jupyterhub/pull/2789) ([@tirkarthi](https://github.com/tirkarthi))
- Log proxy class [#2783](https://github.com/jupyterhub/jupyterhub/pull/2783) ([@GeorgianaElena](https://github.com/GeorgianaElena))
- Add docs for fixtures in CONTRIBUTING.md [#2782](https://github.com/jupyterhub/jupyterhub/pull/2782) ([@kinow](https://github.com/kinow))
- Fix header project name typo [#2775](https://github.com/jupyterhub/jupyterhub/pull/2775) ([@kinow](https://github.com/kinow))
- Remove unused setupegg.py [#2774](https://github.com/jupyterhub/jupyterhub/pull/2774) ([@kinow](https://github.com/kinow))
- Log JupyterHub version on startup [#2752](https://github.com/jupyterhub/jupyterhub/pull/2752) ([@consideRatio](https://github.com/consideRatio))
- Reduce verbosity for "Failing suspected API request to not-running server" (new) [#2751](https://github.com/jupyterhub/jupyterhub/pull/2751) ([@rkdarst](https://github.com/rkdarst))
- Add missing package for json schema doc build [#2744](https://github.com/jupyterhub/jupyterhub/pull/2744) ([@willingc](https://github.com/willingc))
- blacklist urllib3 versions with encoding bug [#2743](https://github.com/jupyterhub/jupyterhub/pull/2743) ([@minrk](https://github.com/minrk))
- Remove tornado deprecated/unnecessary AsyncIOMainLoop().install() call [#2740](https://github.com/jupyterhub/jupyterhub/pull/2740) ([@kinow](https://github.com/kinow))
- Fix deprecated call [#2739](https://github.com/jupyterhub/jupyterhub/pull/2739) ([@kinow](https://github.com/kinow))
- Remove duplicate hub and authenticator traitlets from Spawner [#2736](https://github.com/jupyterhub/jupyterhub/pull/2736) ([@eslavich](https://github.com/eslavich))
- Update issue template [#2725](https://github.com/jupyterhub/jupyterhub/pull/2725) ([@willingc](https://github.com/willingc))
- Use autodoc-traits sphinx extension [#2723](https://github.com/jupyterhub/jupyterhub/pull/2723) ([@willingc](https://github.com/willingc))
- Add New Server: change redirecting to relative to home page in js [#2714](https://github.com/jupyterhub/jupyterhub/pull/2714) ([@bitnik](https://github.com/bitnik))
- Create a warning when creating a service implicitly from service_tokens [#2704](https://github.com/jupyterhub/jupyterhub/pull/2704) ([@katsar0v](https://github.com/katsar0v))
- Fix mistypos [#2702](https://github.com/jupyterhub/jupyterhub/pull/2702) ([@rlukin](https://github.com/rlukin))
- Add Jupyter community link [#2696](https://github.com/jupyterhub/jupyterhub/pull/2696) ([@mattjshannon](https://github.com/mattjshannon))
- Fix failing travis tests [#2695](https://github.com/jupyterhub/jupyterhub/pull/2695) ([@GeorgianaElena](https://github.com/GeorgianaElena))
- Documentation update: hint for using services instead of service tokens. [#2679](https://github.com/jupyterhub/jupyterhub/pull/2679) ([@katsar0v](https://github.com/katsar0v))
- Replace header logo: jupyter -> jupyterhub [#2672](https://github.com/jupyterhub/jupyterhub/pull/2672) ([@consideRatio](https://github.com/consideRatio))
- Update spawn-form example [#2662](https://github.com/jupyterhub/jupyterhub/pull/2662) ([@kinow](https://github.com/kinow))
- Update flask hub authentication services example in doc [#2658](https://github.com/jupyterhub/jupyterhub/pull/2658) ([@cmd-ntrf](https://github.com/cmd-ntrf))
- close `<div class="container">` tag in home.html [#2649](https://github.com/jupyterhub/jupyterhub/pull/2649) ([@bitnik](https://github.com/bitnik))
- Some theme updates; no double NEXT/PREV buttons. [#2647](https://github.com/jupyterhub/jupyterhub/pull/2647) ([@Carreau](https://github.com/Carreau))
- fix typos on technical reference documentation [#2646](https://github.com/jupyterhub/jupyterhub/pull/2646) ([@ilee38](https://github.com/ilee38))
- Update links for Hadoop-related subprojects [#2645](https://github.com/jupyterhub/jupyterhub/pull/2645) ([@jcrist](https://github.com/jcrist))
- corrected docker network create instructions in dockerfiles README [#2632](https://github.com/jupyterhub/jupyterhub/pull/2632) ([@bartolone](https://github.com/bartolone))
- Fixed docs and testing code to use refactored SimpleLocalProcessSpawner [#2631](https://github.com/jupyterhub/jupyterhub/pull/2631) ([@danlester](https://github.com/danlester))
- Update the config used for testing [#2628](https://github.com/jupyterhub/jupyterhub/pull/2628) ([@jtpio](https://github.com/jtpio))
- Update doc: do not suggest depricated config key [#2626](https://github.com/jupyterhub/jupyterhub/pull/2626) ([@lumbric](https://github.com/lumbric))
- Add missing words [#2625](https://github.com/jupyterhub/jupyterhub/pull/2625) ([@remram44](https://github.com/remram44))
- cull-idle: Include a hint on how to add custom culling logic [#2613](https://github.com/jupyterhub/jupyterhub/pull/2613) ([@rkdarst](https://github.com/rkdarst))
- Replace existing redirect code by Tornado's addslash decorator [#2609](https://github.com/jupyterhub/jupyterhub/pull/2609) ([@kinow](https://github.com/kinow))
- Hide Stop My Server red button after server stopped. [#2577](https://github.com/jupyterhub/jupyterhub/pull/2577) ([@aar0nTw](https://github.com/aar0nTw))
- Update link of `changelog` [#2565](https://github.com/jupyterhub/jupyterhub/pull/2565) ([@iblis17](https://github.com/iblis17))
- typo [#2564](https://github.com/jupyterhub/jupyterhub/pull/2564) ([@julienchastang](https://github.com/julienchastang))
- Update to simplify the language related to spawner options [#2558](https://github.com/jupyterhub/jupyterhub/pull/2558) ([@NikeNano](https://github.com/NikeNano))
- Adding the use case of the Elucidata: How Jupyter Notebook is used in… [#2548](https://github.com/jupyterhub/jupyterhub/pull/2548) ([@IamViditAgarwal](https://github.com/IamViditAgarwal))
- Dict rewritten as literal [#2546](https://github.com/jupyterhub/jupyterhub/pull/2546) ([@remyleone](https://github.com/remyleone))

## 1.0

### [1.0.0] 2019-05-03

JupyterHub 1.0 is a major milestone for JupyterHub.
Huge thanks to the many people who have contributed to this release,
whether it was through discussion, testing, documentation, or development.

#### Major new features

- Support TLS encryption and authentication of all internal communication.
  Spawners must implement `.move_certs` method to make certificates available
  to the notebook server if it is not local to the Hub.
- There is now full UI support for managing named servers.
  With named servers, each jupyterhub user may have access to more than one named server. For example, a professor may access a server named `research` and another named `teaching`.

  ![named servers on the home page](./images/named-servers-home.png)
- Authenticators can now expire and refresh authentication data by implementing
  `Authenticator.refresh_user(user)`.
  This allows things like OAuth data and access tokens to be refreshed.
  When used together with `Authenticator.refresh_pre_spawn = True`,
  auth refresh can be forced prior to Spawn,
  allowing the Authenticator to *require* that authentication data is fresh
  immediately before the user's server is launched.

```eval_rst
.. seealso::

  - :meth:`.Authenticator.refresh_user`
  - :meth:`.Spawner.create_certs`
  - :meth:`.Spawner.move_certs`
```

#### New features

- allow custom spawners, authenticators, and proxies to register themselves via 'entry points', enabling more convenient configuration such as:

  ```python
  c.JupyterHub.authenticator_class = 'github'
  c.JupyterHub.spawner_class = 'docker'
  c.JupyterHub.proxy_class = 'traefik_etcd'
  ```
- Spawners are passed the tornado Handler object that requested their spawn (as `self.handler`),
  so they can do things like make decisions based on query arguments in the request.
- SimpleSpawner and DummyAuthenticator, which are useful for testing, have been merged into JupyterHub itself:

  ```python
  # For testing purposes only. Should not be used in production.
  c.JupyterHub.authenticator_class = 'dummy'
  c.JupyterHub.spawner_class = 'simple'
  ```

  These classes are **not** appropriate for production use. Only testing.
- Add health check endpoint at `/hub/health`
- Several prometheus metrics have been added (thanks to [Outreachy](https://www.outreachy.org/) applicants!)
- A new API for registering user activity.
  To prepare for the addition of [alternate proxy implementations](https://github.com/jupyterhub/traefik-proxy),
  responsibility for tracking activity is taken away from the proxy
  and moved to the notebook server (which already has activity tracking features).
  Activity is now tracked by pushing it to the Hub from user servers instead of polling the
  proxy API.
- Dynamic `options_form` callables may now return an empty string
  which will result in no options form being rendered.
- `Spawner.user_options` is persisted to the database to be re-used,
  so that a server spawned once via the form can be re-spawned via the API
  with the same options.
- Added `c.PAMAuthenticator.pam_normalize_username` option for round-tripping
  usernames through PAM to retrieve the normalized form.
- Added `c.JupyterHub.named_server_limit_per_user` configuration to limit
  the number of named servers each user can have.
  The default is 0, for no limit.
- API requests to HubAuthenticated services (e.g. single-user servers)
  may pass a token in the `Authorization` header,
  matching authentication with the Hub API itself.
- Added `Authenticator.is_admin(handler, authentication)` method
  and `Authenticator.admin_groups` configuration for automatically
  determining that a member of a group should be considered an admin.
- New `c.Authenticator.post_auth_hook` configuration
  that can be any callable of the form `async def hook(authenticator, handler, authentication=None):`.
  This hook may transform the return value of `Authenticator.authenticate()`
  and return a new authentication dictionary,
  e.g. specifying admin privileges, group membership,
  or custom white/blacklisting logic.
  This hook is called *after* existing normalization and whitelist checking.
- `Spawner.options_from_form` may now be async
- Added `JupyterHub.shutdown_on_logout` option to trigger shutdown of a user's
  servers when they log out.
- When `Spawner.start` raises an Exception,
  a message can be passed on to the user if the exception has a `.jupyterhub_message` attribute.


#### Changes

- Authentication methods such as `check_whitelist` should now take an additional
  `authentication` argument
  that will be a dictionary (default: None) of authentication data,
  as returned by `Authenticator.authenticate()`:

  ```python
  def check_whitelist(self, username, authentication=None):
      ...
  ```

  `authentication` should have a default value of None
  for backward-compatibility with jupyterhub < 1.0.
- Prometheus metrics page is now authenticated.
  Any authenticated user may see the prometheus metrics.
  To disable prometheus authentication,
  set `JupyterHub.authenticate_prometheus = False`.
- Visits to `/user/:name` no longer trigger an implicit launch of the user's server.
  Instead, a page is shown indicating that the server is not running
  with a link to request the spawn.
- API requests to `/user/:name` for a not-running server will have status 503 instead of 404.
- OAuth includes a confirmation page when attempting to visit another user's server,
  so that users can choose to cancel authentication with the single-user server.
  Confirmation is still skipped when accessing your own server.


#### Fixed

- Various fixes to improve Windows compatibility
  (default Authenticator and Spawner still do not support Windows, but other Spawners may)
- Fixed compatibility with Oracle db
- Fewer redirects following a visit to the default `/` url
- Error when progress is requested before progress is ready
- Error when API requests are made to a not-running server without authentication
- Avoid logging database password on connect if password is specified in `JupyterHub.db_url`.

#### Development changes

There have been several changes to the development process that shouldn't
generally affect users of JupyterHub, but may affect contributors.
In general, see `CONTRIBUTING.md` for contribution info or ask if you have questions.

- JupyterHub has adopted `black` as a code autoformatter and `pre-commit`
  as a tool for automatically running code formatting on commit.
  This is meant to make it *easier* to contribute to JupyterHub,
  so let us know if it's having the opposite effect.
- JupyterHub has switched its test suite to using `pytest-asyncio` from `pytest-tornado`.
- OAuth is now implemented internally using `oauthlib` instead of `python-oauth2`. This should have no effect on behavior.


## 0.9

### [0.9.6] 2019-04-01

JupyterHub 0.9.6 is a security release.

- Fixes an Open Redirect vulnerability (CVE-2019-10255).

JupyterHub 0.9.5 included a partial fix for this issue.

### [0.9.4] 2018-09-24

JupyterHub 0.9.4 is a small bugfix release.

- Fixes an  issue that required all running user servers to be restarted
  when performing an upgrade from 0.8 to 0.9.
- Fixes content-type for API endpoints back to `application/json`.
  It was `text/html` in 0.9.0-0.9.3.

### [0.9.3] 2018-09-12

JupyterHub 0.9.3 contains small bugfixes and improvements

- Fix token page and model handling of `expires_at`.
  This field was missing from the REST API model for tokens
  and could cause the token page to not render
- Add keep-alive to progress event stream to avoid proxies dropping
  the connection due to inactivity
- Documentation and example improvements
- Disable quit button when using notebook 5.6
- Prototype new feature (may change prior to 1.0):
  pass requesting Handler to Spawners during start,
  accessible as `self.handler`

### [0.9.2] 2018-08-10

JupyterHub 0.9.2 contains small bugfixes and improvements.

- Documentation and example improvements
- Add `Spawner.consecutive_failure_limit` config for aborting the Hub if too many spawns fail in a row.
- Fix for handling SIGTERM when run with asyncio (tornado 5)
- Windows compatibility fixes


### [0.9.1] 2018-07-04

JupyterHub 0.9.1 contains a number of small bugfixes on top of 0.9.

- Use a PID file for the proxy to decrease the likelihood that a leftover proxy process will prevent JupyterHub from restarting
- `c.LocalProcessSpawner.shell_cmd` is now configurable
- API requests to stopped servers (requests to the hub for `/user/:name/api/...`) fail with 404 rather than triggering a restart of the server
- Compatibility fix for notebook 5.6.0 which will introduce further
  security checks for local connections
- Managed services always use localhost to talk to the Hub if the Hub listening on all interfaces
- When using a URL prefix, the Hub route will be `JupyterHub.base_url` instead of unconditionally `/`
- additional fixes and improvements

### [0.9.0] 2018-06-15

JupyterHub 0.9 is a major upgrade of JupyterHub.
There are several changes to the database schema,
so make sure to backup your database and run:

    jupyterhub upgrade-db

after upgrading jupyterhub.

The biggest change for 0.9 is the switch to asyncio coroutines everywhere
instead of tornado coroutines. Custom Spawners and Authenticators are still
free to use tornado coroutines for async methods, as they will continue to
work. As part of this upgrade, JupyterHub 0.9 drops support for Python < 3.5
and tornado < 5.0.


#### Changed

- Require Python >= 3.5
- Require tornado >= 5.0
- Use asyncio coroutines throughout
- Set status 409 for conflicting actions instead of 400,
  e.g. creating users or groups that already exist.
- timestamps in REST API continue to be UTC, but now include 'Z' suffix
  to identify them as such.
- REST API User model always includes `servers` dict,
  not just when named servers are enabled.
- `server` info is no longer available to oauth identification endpoints,
  only user info and group membership.
- `User.last_activity` may be None if a user has not been seen,
  rather than starting with the user creation time
  which is now separately stored as `User.created`.
- static resources are now found in `$PREFIX/share/jupyterhub` instead of `share/jupyter/hub` for improved consistency.
- Deprecate `.extra_log_file` config. Use pipe redirection instead:

      jupyterhub &>> /var/log/jupyterhub.log

- Add `JupyterHub.bind_url` config for setting the full bind URL of the proxy.
  Sets ip, port, base_url all at once.
- Add `JupyterHub.hub_bind_url` for setting the full host+port of the Hub.
  `hub_bind_url` supports unix domain sockets, e.g.
  `unix+http://%2Fsrv%2Fjupyterhub.sock`
- Deprecate `JupyterHub.hub_connect_port` config in favor of `JupyterHub.hub_connect_url`. `hub_connect_ip` is not deprecated
  and can still be used in the common case where only the ip address of the hub differs from the bind ip.

#### Added

- Spawners can define a `.progress` method which should be an async generator.
  The generator should yield events of the form:
  ```python
  {
    "message": "some-state-message",
    "progress": 50,
  }
  ```
  These messages will be shown with a progress bar on the spawn-pending page.
  The `async_generator` package can be used to make async generators
  compatible with Python 3.5.
- track activity of individual API tokens
- new REST API for managing API tokens at `/hub/api/user/tokens[/token-id]`
- allow viewing/revoking tokens via token page
- User creation time is available in the REST API as `User.created`
- Server start time is stored as `Server.started`
- `Spawner.start` may return a URL for connecting to a notebook instead of `(ip, port)`. This enables Spawners to launch servers that setup their own HTTPS.
- Optimize database performance by disabling sqlalchemy expire_on_commit by default.
- Add `python -m jupyterhub.dbutil shell` entrypoint for quickly
  launching an IPython session connected to your JupyterHub database.
- Include `User.auth_state` in user model on single-user REST endpoints for admins only.
- Include `Server.state` in server model on REST endpoints for admins only.
- Add `Authenticator.blacklist` for blacklisting users instead of whitelisting.
- Pass `c.JupyterHub.tornado_settings['cookie_options']` down to Spawners
  so that cookie options (e.g. `expires_days`) can be set globally for the whole application.
- SIGINFO (`ctrl-t`) handler showing the current status of all running threads,
  coroutines, and CPU/memory/FD consumption.
- Add async `Spawner.get_options_form` alternative to `.options_form`, so it can be a coroutine.
- Add `JupyterHub.redirect_to_server` config to govern whether
  users should be sent to their server on login or the JupyterHub home page.
- html page templates can be more easily customized and extended.
- Allow registering external OAuth clients for using the Hub as an OAuth provider.
- Add basic prometheus metrics at `/hub/metrics` endpoint.
- Add session-id cookie, enabling immediate revocation of login tokens.
- Authenticators may specify that users are admins by specifying the `admin` key when return the user model as a dict.
- Added "Start All" button to admin page for launching all user servers at once.
- Services have an `info` field which is a dictionary.
  This is accessible via the REST API.
- `JupyterHub.extra_handlers` allows defining additional tornado RequestHandlers attached to the Hub.
- API tokens may now expire.
  Expiry is available in the REST model as `expires_at`,
  and settable when creating API tokens by specifying `expires_in`.


#### Fixed

- Remove green from theme to improve accessibility
- Fix error when proxy deletion fails due to route already being deleted
- clear `?redirects` from URL on successful launch
- disable send2trash by default, which is rarely desirable for jupyterhub
- Put PAM calls in a thread so they don't block the main application
  in cases where PAM is slow (e.g. LDAP).
- Remove implicit spawn from login handler,
  instead relying on subsequent request for `/user/:name` to trigger spawn.
- Fixed several inconsistencies for initial redirects,
  depending on whether server is running or not and whether the user is logged in or not.
- Admin requests for  `/user/:name` (when admin-access is enabled) launch the right server if it's not running instead of redirecting to their own.
- Major performance improvement starting up JupyterHub with many users,
  especially when most are inactive.
- Various fixes in race conditions and performance improvements with the default proxy.
- Fixes for CORS headers
- Stop setting `.form-control` on spawner form inputs unconditionally.
- Better recovery from database errors and database connection issues
  without having to restart the Hub.
- Fix handling of `~` character in usernames.
- Fix jupyterhub startup when `getpass.getuser()` would fail,
  e.g. due to missing entry in passwd file in containers.


## 0.8

### [0.8.1] 2017-11-07

JupyterHub 0.8.1 is a collection of bugfixes and small improvements on 0.8.

#### Added

- Run tornado with AsyncIO by default
- Add `jupyterhub --upgrade-db` flag for automatically upgrading the database as part of startup.
  This is useful for cases where manually running `jupyterhub upgrade-db`
  as a separate step is unwieldy.
- Avoid creating backups of the database when no changes are to be made by
  `jupyterhub upgrade-db`.

#### Fixed

- Add some further validation to usernames - `/` is not allowed in usernames.
- Fix empty logout page when using auto_login
- Fix autofill of username field in default login form.
- Fix listing of users on the admin page who have not yet started their server.
- Fix ever-growing traceback when re-raising Exceptions from spawn failures.
- Remove use of deprecated `bower` for javascript client dependencies.


### [0.8.0] 2017-10-03

JupyterHub 0.8 is a big release!

Perhaps the biggest change is the use of OAuth to negotiate authentication
between the Hub and single-user services.
Due to this change, it is important that the single-user server
and Hub are both running the same version of JupyterHub.
If you are using containers (e.g. via DockerSpawner or KubeSpawner),
this means upgrading jupyterhub in your user images at the same time as the Hub.
In most cases, a

    pip install jupyterhub==version

in your Dockerfile is sufficient.

#### Added

- JupyterHub now defined a `Proxy` API for custom
  proxy implementations other than the default.
  The defaults are unchanged,
  but configuration of the proxy is now done on the `ConfigurableHTTPProxy` class instead of the top-level JupyterHub.
  TODO: docs for writing a custom proxy.
- Single-user servers and services
  (anything that uses HubAuth)
  can now accept token-authenticated requests via the Authentication header.
- Authenticators can now store state in the Hub's database.
  To do so, the `authenticate` method should return a dict of the form

  ```python
  {
      'username': 'name',
      'state': {}
  }
  ```

  This data will be encrypted and requires `JUPYTERHUB_CRYPT_KEY` environment variable to be set
  and the `Authenticator.enable_auth_state` flag to be True.
  If these are not set, auth_state returned by the Authenticator will not be stored.
- There is preliminary support for multiple (named) servers per user in the REST API.
  Named servers can be created via API requests, but there is currently no UI for managing them.
- Add `LocalProcessSpawner.popen_kwargs` and `LocalProcessSpawner.shell_cmd`
  for customizing how user server processes are launched.
- Add `Authenticator.auto_login` flag for skipping the "Login with..." page explicitly.
- Add `JupyterHub.hub_connect_ip` configuration
  for the ip that should be used when connecting to the Hub.
  This is promoting (and deprecating) `DockerSpawner.hub_ip_connect`
  for use by all Spawners.
- Add `Spawner.pre_spawn_hook(spawner)` hook for customizing
  pre-spawn events.
- Add `JupyterHub.active_server_limit` and `JupyterHub.concurrent_spawn_limit`
  for limiting the total number of running user servers and the number of pending spawns, respectively.


#### Changed

- more arguments to spawners are now passed via environment variables (`.get_env()`)
  rather than CLI arguments (`.get_args()`)
- internally generated tokens no longer get extra hash rounds,
  significantly speeding up authentication.
  The hash rounds were deemed unnecessary because the tokens were already
  generated with high entropy.
- `JUPYTERHUB_API_TOKEN` env is available at all times,
  rather than being removed during single-user start.
  The token is now accessible to kernel processes,
  enabling user kernels to make authenticated API requests to Hub-authenticated services.
- Cookie secrets should be 32B hex instead of large base64 secrets.
- pycurl is used by default, if available.

#### Fixed

So many things fixed!

- Collisions are checked when users are renamed
- Fix bug where OAuth authenticators could not logout users
  due to being redirected right back through the login process.
- If there are errors loading your config files,
  JupyterHub will refuse to start with an informative error.
  Previously, the bad config would be ignored and JupyterHub would launch with default configuration.
- Raise 403 error on unauthorized user rather than redirect to login,
  which could cause redirect loop.
- Set `httponly` on cookies because it's prudent.
- Improve support for MySQL as the database backend
- Many race conditions and performance problems under heavy load have been fixed.
- Fix alembic tagging of database schema versions.

#### Removed

- End support for Python 3.3 

## 0.7

### [0.7.2] - 2017-01-09

#### Added

- Support service environment variables and defaults in `jupyterhub-singleuser`
  for easier deployment of notebook servers as a Service.
- Add `--group` parameter for deploying `jupyterhub-singleuser` as a Service with group authentication.
- Include URL parameters when redirecting through `/user-redirect/`

### Fixed

- Fix group authentication for HubAuthenticated services

### [0.7.1] - 2017-01-02

#### Added

- `Spawner.will_resume` for signaling that a single-user server is paused instead of stopped.
  This is needed for cases like `DockerSpawner.remove_containers = False`,
  where the first API token is re-used for subsequent spawns.
- Warning on startup about single-character usernames,
   caused by common `set('string')` typo in config.

#### Fixed

- Removed spurious warning about empty `next_url`, which is AOK.

### [0.7.0] - 2016-12-2

#### Added

- Implement Services API [\#705](https://github.com/jupyterhub/jupyterhub/pull/705)
- Add `/api/` and `/api/info` endpoints [\#675](https://github.com/jupyterhub/jupyterhub/pull/675)
- Add documentation for JupyterLab, pySpark configuration, troubleshooting,
  and more.
- Add logging of error if adding users already in database.  [\#689](https://github.com/jupyterhub/jupyterhub/pull/689)
- Add HubAuth class for authenticating with JupyterHub. This class can
  be used by any application, even outside tornado.
- Add user groups.
- Add `/hub/user-redirect/...` URL for redirecting users to a file on their own server.


#### Changed

- Always install with setuptools but not eggs (effectively require
  `pip install .`) [\#722](https://github.com/jupyterhub/jupyterhub/pull/722)
- Updated formatting of changelog. [\#711](https://github.com/jupyterhub/jupyterhub/pull/711)
- Single-user server is provided by JupyterHub package, so single-user servers depend on JupyterHub now.

#### Fixed

- Fix docker repository location [\#719](https://github.com/jupyterhub/jupyterhub/pull/719)
- Fix swagger spec conformance and timestamp type in API spec
- Various redirect-loop-causing bugs have been fixed.


#### Removed

- Deprecate `--no-ssl` command line option. It has no meaning and warns if
  used. [\#789](https://github.com/jupyterhub/jupyterhub/pull/789)
- Deprecate `%U` username substitution in favor of `{username}`. [\#748](https://github.com/jupyterhub/jupyterhub/pull/748)
- Removed deprecated SwarmSpawner link.  [\#699](https://github.com/jupyterhub/jupyterhub/pull/699)

## 0.6

### [0.6.1] - 2016-05-04

Bugfixes on 0.6:

- statsd is an optional dependency, only needed if in use
- Notice more quickly when servers have crashed
- Better error pages for proxy errors
- Add Stop All button to admin panel for stopping all servers at once

### [0.6.0] - 2016-04-25

- JupyterHub has moved to a new `jupyterhub` namespace on GitHub and Docker. What was `juptyer/jupyterhub` is now `jupyterhub/jupyterhub`, etc.
- `jupyterhub/jupyterhub` image on DockerHub no longer loads the jupyterhub_config.py in an ONBUILD step. A new `jupyterhub/jupyterhub-onbuild` image does this
- Add statsd support, via `c.JupyterHub.statsd_{host,port,prefix}`
- Update to traitlets 4.1 `@default`, `@observe` APIs for traits
- Allow disabling PAM sessions via `c.PAMAuthenticator.open_sessions = False`. This may be needed on SELinux-enabled systems, where our PAM session logic often does not work properly
- Add `Spawner.environment` configurable, for defining extra environment variables to load for single-user servers
- JupyterHub API tokens can be pregenerated and loaded via `JupyterHub.api_tokens`, a dict of `token: username`.
- JupyterHub API tokens can be requested via the REST API, with a POST request to `/api/authorizations/token`.
  This can only be used if the Authenticator has a username and password.
- Various fixes for user URLs and redirects


## [0.5] - 2016-03-07


- Single-user server must be run with Jupyter Notebook ≥ 4.0
- Require `--no-ssl` confirmation to allow the Hub to be run without SSL (e.g. behind SSL termination in nginx)
- Add lengths to text fields for MySQL support
- Add `Spawner.disable_user_config` for preventing user-owned configuration from modifying single-user servers.
- Fixes for MySQL support.
- Add ability to run each user's server on its own subdomain. Requires wildcard DNS and wildcard SSL to be feasible. Enable subdomains by setting `JupyterHub.subdomain_host = 'https://jupyterhub.domain.tld[:port]'`.
- Use `127.0.0.1` for local communication instead of `localhost`, avoiding issues with DNS on some systems.
- Fix race that could add users to proxy prematurely if spawning is slow.

## 0.4

### [0.4.1] - 2016-02-03

Fix removal of `/login` page in 0.4.0, breaking some OAuth providers.

### [0.4.0] - 2016-02-01

- Add `Spawner.user_options_form` for specifying an HTML form to present to users,
  allowing users to influence the spawning of their own servers.
- Add `Authenticator.pre_spawn_start` and `Authenticator.post_spawn_stop` hooks,
  so that Authenticators can do setup or teardown (e.g. passing credentials to Spawner,
  mounting data sources, etc.).
  These methods are typically used with custom Authenticator+Spawner pairs.
- 0.4 will be the last JupyterHub release where single-user servers running IPython 3 is supported instead of Notebook ≥ 4.0.


## [0.3] - 2015-11-04

- No longer make the user starting the Hub an admin
- start PAM sessions on login
- hooks for Authenticators to fire before spawners start and after they stop,
  allowing deeper interaction between Spawner/Authenticator pairs.
- login redirect fixes

## [0.2] - 2015-07-12

- Based on standalone traitlets instead of IPython.utils.traitlets
- multiple users in admin panel
- Fixes for usernames that require escaping

## 0.1 - 2015-03-07

First preview release


[Unreleased]: https://github.com/jupyterhub/jupyterhub/compare/1.0.0...HEAD
[1.0.0]: https://github.com/jupyterhub/jupyterhub/compare/0.9.6...1.0.0
[0.9.6]: https://github.com/jupyterhub/jupyterhub/compare/0.9.4...0.9.6
[0.9.4]: https://github.com/jupyterhub/jupyterhub/compare/0.9.3...0.9.4
[0.9.3]: https://github.com/jupyterhub/jupyterhub/compare/0.9.2...0.9.3
[0.9.2]: https://github.com/jupyterhub/jupyterhub/compare/0.9.1...0.9.2
[0.9.1]: https://github.com/jupyterhub/jupyterhub/compare/0.9.0...0.9.1
[0.9.0]: https://github.com/jupyterhub/jupyterhub/compare/0.8.1...0.9.0
[0.8.1]: https://github.com/jupyterhub/jupyterhub/compare/0.8.0...0.8.1
[0.8.0]: https://github.com/jupyterhub/jupyterhub/compare/0.7.2...0.8.0
[0.7.2]: https://github.com/jupyterhub/jupyterhub/compare/0.7.1...0.7.2
[0.7.1]: https://github.com/jupyterhub/jupyterhub/compare/0.7.0...0.7.1
[0.7.0]: https://github.com/jupyterhub/jupyterhub/compare/0.6.1...0.7.0
[0.6.1]: https://github.com/jupyterhub/jupyterhub/compare/0.6.0...0.6.1
[0.6.0]: https://github.com/jupyterhub/jupyterhub/compare/0.5.0...0.6.0
[0.5]: https://github.com/jupyterhub/jupyterhub/compare/0.4.1...0.5.0
[0.4.1]: https://github.com/jupyterhub/jupyterhub/compare/0.4.0...0.4.1
[0.4.0]: https://github.com/jupyterhub/jupyterhub/compare/0.3.0...0.4.0
[0.3]: https://github.com/jupyterhub/jupyterhub/compare/0.2.0...0.3.0
[0.2]: https://github.com/jupyterhub/jupyterhub/compare/0.1.0...0.2.0
