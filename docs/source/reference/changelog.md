(changelog)=

# Changelog

For detailed changes from the prior release, click on the version number, and
its link will bring up a GitHub listing of changes. Use `git log` on the
command line for details.

## Versioning

JupyterHub follows Intended Effort Versioning ([EffVer](https://jacobtomlinson.dev/effver/)) for versioning,
where the version number is meant to indicate the amount of effort required to upgrade to the new version.

Contributors to major version bumps in JupyterHub include:

- Database schema changes that require migrations and are hard to roll back
- Increasing the minimum required Python version
- Large new features
- Breaking changes likely to affect users

## [Unreleased]

## 5.1

### 5.1.0 - 2024-07-31

JupyterHub 5.1 is a small release adding a few refinements and new features on top of 5.0.
5.1 has no known changes in compatibility relative to 5.0.

5.1.0 is also a **security release**, fixing [CVE-2024-41942] (also backported to 4.1.6).
All JupyterHub deployments are encouraged to upgrade,
but only those with users having the `admin:users` scope are affected.
The [full advisory][CVE-2024-41942] will be published 7 days after the release.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/5.0.0...5.1.0))

#### New features added

- Add token_expires_in_max_seconds configuration [#4831](https://github.com/jupyterhub/jupyterhub/pull/4831) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics), [@rcthomas](https://github.com/rcthomas))
- Add Spawner.group_overrides to allow overriding spawner config based on user group membership [#4822](https://github.com/jupyterhub/jupyterhub/pull/4822) ([@yuvipanda](https://github.com/yuvipanda), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics), [@ryanlovett](https://github.com/ryanlovett))

#### Enhancements made

- Show insecure login warning when not in a secure context [#4856](https://github.com/jupyterhub/jupyterhub/pull/4856) ([@jfrost-mo](https://github.com/jfrost-mo), [@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- allow stop while start is pending [#4844](https://github.com/jupyterhub/jupyterhub/pull/4844) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- reduce cost of event_loop_interval metric [#4835](https://github.com/jupyterhub/jupyterhub/pull/4835) ([@minrk](https://github.com/minrk), [@yuvipanda](https://github.com/yuvipanda))

#### Bugs fixed

- Pass `kwargs` down to `initialize()` call of the server [#4860](https://github.com/jupyterhub/jupyterhub/pull/4860) ([@krassowski](https://github.com/krassowski), [@minrk](https://github.com/minrk))

#### Documentation improvements

- Provide consistent myst references to documentation pages - part 1 [#4837](https://github.com/jupyterhub/jupyterhub/pull/4837) ([@yuvipanda](https://github.com/yuvipanda), [@minrk](https://github.com/minrk))
- fix formatting of group_overrides docstring [#4836](https://github.com/jupyterhub/jupyterhub/pull/4836) ([@minrk](https://github.com/minrk), [@yuvipanda](https://github.com/yuvipanda))
- Fix wording for `read:users` scope description [#4829](https://github.com/jupyterhub/jupyterhub/pull/4829) ([@manics](https://github.com/manics), [@consideRatio](https://github.com/consideRatio))
- further emphasize that admin_users config only grants permission [#4828](https://github.com/jupyterhub/jupyterhub/pull/4828) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- Jupyter(Hub) conceptual intro [#2726](https://github.com/jupyterhub/jupyterhub/pull/2726) ([@rkdarst](https://github.com/rkdarst), [@yuvipanda](https://github.com/yuvipanda), [@betatim](https://github.com/betatim), [@choldgraf](https://github.com/choldgraf), [@rcthomas](https://github.com/rcthomas), [@consideRatio](https://github.com/consideRatio), [@willingc](https://github.com/willingc), [@manics](https://github.com/manics))

#### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2024-05-24&to=2024-07-30&type=c))

@benz0li ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abenz0li+updated%3A2024-05-24..2024-07-30&type=Issues)) | @betatim ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abetatim+updated%3A2024-05-24..2024-07-30&type=Issues)) | @choldgraf ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acholdgraf+updated%3A2024-05-24..2024-07-30&type=Issues)) | @consideRatio ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2024-05-24..2024-07-30&type=Issues)) | @jfrost-mo ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajfrost-mo+updated%3A2024-05-24..2024-07-30&type=Issues)) | @krassowski ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akrassowski+updated%3A2024-05-24..2024-07-30&type=Issues)) | @Mackenzie-OO7 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AMackenzie-OO7+updated%3A2024-05-24..2024-07-30&type=Issues)) | @manics ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2024-05-24..2024-07-30&type=Issues)) | @marto1 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amarto1+updated%3A2024-05-24..2024-07-30&type=Issues)) | @minrk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2024-05-24..2024-07-30&type=Issues)) | @rcthomas ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arcthomas+updated%3A2024-05-24..2024-07-30&type=Issues)) | @rkdarst ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arkdarst+updated%3A2024-05-24..2024-07-30&type=Issues)) | @ryanlovett ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aryanlovett+updated%3A2024-05-24..2024-07-30&type=Issues)) | @willingc ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awillingc+updated%3A2024-05-24..2024-07-30&type=Issues)) | @yuvipanda ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2024-05-24..2024-07-30&type=Issues))

## 5.0

### 5.0.0 - 2024-05-25

5.0.0 is a major release of JupyterHub.
It has lots of cool new features.

For information about upgrading, see [upgrading to 5.0 documentation](howto:upgrading-v5).

Changes that are likely to require effort to upgrade:

- New JupyterHub.subdomain_hook and default subdomain scheme
  is more reliable and should work for all usernames.
- JupyterHub now requires Python 3.8
- New `Authenticator.allow_all` and `allow_existing_users` configuration options.
  Implicitly allowing all authenticated users when no explicit `allow` config is provided is no longer the default.
- bootstrap is upgraded to 5.3, which may require upgrading if you have custom page templates or use `Spawner.options_form`

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/4.0.2...5.0.0))

#### API and Breaking Changes

- switch from jupyter-telemetry to jupyter-events [#4807](https://github.com/jupyterhub/jupyterhub/pull/4807) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- update bootstrap to v5 [#4774](https://github.com/jupyterhub/jupyterhub/pull/4774) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- explicitly require groups in auth model when Authenticator.manage_groups is enabled [#4645](https://github.com/jupyterhub/jupyterhub/pull/4645) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- add JupyterHub.subdomain_hook [#4471](https://github.com/jupyterhub/jupyterhub/pull/4471) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@akhmerov](https://github.com/akhmerov))

#### New features added

- add full_url, full_progress_url to server models [#4798](https://github.com/jupyterhub/jupyterhub/pull/4798) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- add token_id to `/api/user` [#4790](https://github.com/jupyterhub/jupyterhub/pull/4790) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Add authenticator-managed roles (`manage_roles`) [#4748](https://github.com/jupyterhub/jupyterhub/pull/4748) ([@krassowski](https://github.com/krassowski), [@minrk](https://github.com/minrk))
- server-side sorting of admin page [#4722](https://github.com/jupyterhub/jupyterhub/pull/4722) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Implement sort order in GET /users [#4721](https://github.com/jupyterhub/jupyterhub/pull/4721) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- admin: persist page view parameters in url [#4720](https://github.com/jupyterhub/jupyterhub/pull/4720) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- allow callable values in c.JupyterHub.template_vars [#4717](https://github.com/jupyterhub/jupyterhub/pull/4717) ([@kreuzert](https://github.com/kreuzert), [@minrk](https://github.com/minrk))
- Add Authenticator config `allow_all` and `allow_existing_users` [#4701](https://github.com/jupyterhub/jupyterhub/pull/4701) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- add Spawner.poll_jitter [#4648](https://github.com/jupyterhub/jupyterhub/pull/4648) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics), [@rcthomas](https://github.com/rcthomas))
- add event_loop_interval_seconds metric [#4615](https://github.com/jupyterhub/jupyterhub/pull/4615) ([@minrk](https://github.com/minrk), [@yuvipanda](https://github.com/yuvipanda))
- user-initiated sharing [#4594](https://github.com/jupyterhub/jupyterhub/pull/4594) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@sgaist](https://github.com/sgaist), [@manics](https://github.com/manics), [@krassowski](https://github.com/krassowski))
- Improve requests for tokens with scopes [#4578](https://github.com/jupyterhub/jupyterhub/pull/4578) ([@minrk](https://github.com/minrk))
- Add `JUPYTERHUB_METRICS_PREFIX` environment variable to customize metrics prefix [#4525](https://github.com/jupyterhub/jupyterhub/pull/4525) ([@danilopeixoto](https://github.com/danilopeixoto), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@nreith](https://github.com/nreith), [@manics](https://github.com/manics))
- Support Jupyverse as a single-user server [#4520](https://github.com/jupyterhub/jupyterhub/pull/4520) ([@davidbrochart](https://github.com/davidbrochart), [@minrk](https://github.com/minrk))
- add JupyterHub.public_url config [#4479](https://github.com/jupyterhub/jupyterhub/pull/4479) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics), [@yuvipanda](https://github.com/yuvipanda))
- add JupyterHub.subdomain_hook [#4471](https://github.com/jupyterhub/jupyterhub/pull/4471) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@akhmerov](https://github.com/akhmerov))

#### Enhancements made

- add full URLs to share models [#4817](https://github.com/jupyterhub/jupyterhub/pull/4817) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- quieter logging in activity-reporting when hub is temporarily unavailable [#4814](https://github.com/jupyterhub/jupyterhub/pull/4814) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Token UI: move button to after form fields [#4783](https://github.com/jupyterhub/jupyterhub/pull/4783) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Support forbidding unauthenticated access (`allow_unauthenticated_access = False`) [#4779](https://github.com/jupyterhub/jupyterhub/pull/4779) ([@krassowski](https://github.com/krassowski), [@minrk](https://github.com/minrk))
- Compare major hub and singleuser versions only [#4658](https://github.com/jupyterhub/jupyterhub/pull/4658) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Log token deletions via API [#4644](https://github.com/jupyterhub/jupyterhub/pull/4644) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- add warning when an oauth client is used after its secret is deleted [#4643](https://github.com/jupyterhub/jupyterhub/pull/4643) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Include LDAP groups in local spawner gids [#4628](https://github.com/jupyterhub/jupyterhub/pull/4628) ([@uellue](https://github.com/uellue), [@minrk](https://github.com/minrk))
- move service oauth state from cookies to memory [#4608](https://github.com/jupyterhub/jupyterhub/pull/4608) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@sgaist](https://github.com/sgaist), [@yuvipanda](https://github.com/yuvipanda))
- only show links to services users have access to [#4585](https://github.com/jupyterhub/jupyterhub/pull/4585) ([@marcwit](https://github.com/marcwit), [@minrk](https://github.com/minrk))
- service auth: Don't log user model on auth by default [#4572](https://github.com/jupyterhub/jupyterhub/pull/4572) ([@diocas](https://github.com/diocas), [@minrk](https://github.com/minrk))
- only set 'domain' field on session-id cookie [#4563](https://github.com/jupyterhub/jupyterhub/pull/4563) ([@minrk](https://github.com/minrk))
- Improve debugging when waiting for servers [#4561](https://github.com/jupyterhub/jupyterhub/pull/4561) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Improve query performance with eager loading [#4494](https://github.com/jupyterhub/jupyterhub/pull/4494) ([@minrk](https://github.com/minrk), [@ryanlovett](https://github.com/ryanlovett))

#### Bugs fixed

- Fix missing `form-control` classes & some padding on named servers [#4821](https://github.com/jupyterhub/jupyterhub/pull/4821) ([@yuvipanda](https://github.com/yuvipanda), [@minrk](https://github.com/minrk))
- admin: don't use state change to update offset [#4815](https://github.com/jupyterhub/jupyterhub/pull/4815) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- use os.getgrouplist to check group membership in allowed_groups [#4806](https://github.com/jupyterhub/jupyterhub/pull/4806) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- include domain in PrefixRedirectHandler [#4805](https://github.com/jupyterhub/jupyterhub/pull/4805) ([@minrk](https://github.com/minrk), [@johnpmayer](https://github.com/johnpmayer))
- 403 instead of redirect for token-only HubAuth [#4797](https://github.com/jupyterhub/jupyterhub/pull/4797) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- Fix counts on list users queries [#4794](https://github.com/jupyterhub/jupyterhub/pull/4794) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- set login cookie if user changed [#4739](https://github.com/jupyterhub/jupyterhub/pull/4739) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Catch ValueError while waiting for server to be reachable [#4733](https://github.com/jupyterhub/jupyterhub/pull/4733) ([@kreuzert](https://github.com/kreuzert), [@minrk](https://github.com/minrk))
- resolve paths in disable_user_config [#4713](https://github.com/jupyterhub/jupyterhub/pull/4713) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@lumberbot-app](https://github.com/lumberbot-app))
- Unescape jinja username [#4679](https://github.com/jupyterhub/jupyterhub/pull/4679) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk), [@lumberbot-app](https://github.com/lumberbot-app))
- Improve validation, docs for token.expires_in [#4677](https://github.com/jupyterhub/jupyterhub/pull/4677) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- avoid attempting to patch removed IPythonHandler with notebook v7 [#4651](https://github.com/jupyterhub/jupyterhub/pull/4651) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- simplify, avoid errors in parsing accept headers [#4632](https://github.com/jupyterhub/jupyterhub/pull/4632) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics), [@lumberbot-app](https://github.com/lumberbot-app))
- avoid setting unused oauth state cookies on API requests [#4630](https://github.com/jupyterhub/jupyterhub/pull/4630) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@mbiette](https://github.com/mbiette), [@lumberbot-app](https://github.com/lumberbot-app))
- fix package_data in docker images [#4596](https://github.com/jupyterhub/jupyterhub/pull/4596) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@lumberbot-app](https://github.com/lumberbot-app))
- fix mutation of frozenset in scope intersection [#4570](https://github.com/jupyterhub/jupyterhub/pull/4570) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Use {base_url}/api for checking hub version [#4567](https://github.com/jupyterhub/jupyterhub/pull/4567) ([@jabbera](https://github.com/jabbera), [@minrk](https://github.com/minrk))
- Use `user.stop` to cleanup spawners that stopped while Hub was down [#4562](https://github.com/jupyterhub/jupyterhub/pull/4562) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- singleuser extension: persist token from ?token=... url in cookie [#4560](https://github.com/jupyterhub/jupyterhub/pull/4560) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@kzgrzendek](https://github.com/kzgrzendek))
- fail if external oauth service lacks required oauth_redirect_uri [#4555](https://github.com/jupyterhub/jupyterhub/pull/4555) ([@minrk](https://github.com/minrk), [@yuvipanda](https://github.com/yuvipanda), [@consideRatio](https://github.com/consideRatio), [@lumberbot-app](https://github.com/lumberbot-app))
- Fix include_stopped_servers in paginated next_url [#4542](https://github.com/jupyterhub/jupyterhub/pull/4542) ([@jabbera](https://github.com/jabbera), [@minrk](https://github.com/minrk))

#### Maintenance and upkeep improvements

- DOC: /share-codes/ url typo [#4816](https://github.com/jupyterhub/jupyterhub/pull/4816) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- ci: enable pip cache [#4812](https://github.com/jupyterhub/jupyterhub/pull/4812) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- Update string formatting - from %s to f-strings [#4808](https://github.com/jupyterhub/jupyterhub/pull/4808) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Relax dependency on async_generator [#4799](https://github.com/jupyterhub/jupyterhub/pull/4799) ([@lahwaacz](https://github.com/lahwaacz), [@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- increase docker build timeout to 30 minutes [#4795](https://github.com/jupyterhub/jupyterhub/pull/4795) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- adopt djlint linter/autoformatter for jinja templates [#4793](https://github.com/jupyterhub/jupyterhub/pull/4793) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- test: avoid producing '[group]' string in output [#4782](https://github.com/jupyterhub/jupyterhub/pull/4782) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@krassowski](https://github.com/krassowski))
- clarify error template debug log [#4781](https://github.com/jupyterhub/jupyterhub/pull/4781) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- forward-port 4.1.5 [#4776](https://github.com/jupyterhub/jupyterhub/pull/4776) ([@minrk](https://github.com/minrk))
- forward-port 4.1.4 [#4765](https://github.com/jupyterhub/jupyterhub/pull/4765) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Forward-port xsrf patches from 4.1.3 [#4755](https://github.com/jupyterhub/jupyterhub/pull/4755) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@jrdnbradford](https://github.com/jrdnbradford))
- forward-port changes for 4.1.1 [#4747](https://github.com/jupyterhub/jupyterhub/pull/4747) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- run browser tests in subdomain [#4738](https://github.com/jupyterhub/jupyterhub/pull/4738) ([@minrk](https://github.com/minrk))
- avoid duplicate jupyterhub installation for docs [#4737](https://github.com/jupyterhub/jupyterhub/pull/4737) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- switch to ruff for lint, format [#4724](https://github.com/jupyterhub/jupyterhub/pull/4724) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- admin: update navigation for react-router v6 [#4723](https://github.com/jupyterhub/jupyterhub/pull/4723) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Update `black.target_version` in `pyproject.toml` [#4712](https://github.com/jupyterhub/jupyterhub/pull/4712) ([@Ph0tonic](https://github.com/Ph0tonic), [@consideRatio](https://github.com/consideRatio))
- bump pythons, base images on CI [#4704](https://github.com/jupyterhub/jupyterhub/pull/4704) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- test Python 3.12 [#4703](https://github.com/jupyterhub/jupyterhub/pull/4703) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- enable log capture in pytest, compatibility with pytest 8 [#4684](https://github.com/jupyterhub/jupyterhub/pull/4684) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- don't run check_allowed until after check_blocked_users resolves [#4683](https://github.com/jupyterhub/jupyterhub/pull/4683) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- avoid deprecated datetime.utcnow [#4665](https://github.com/jupyterhub/jupyterhub/pull/4665) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- temporarily pin pytest-asyncio [#4663](https://github.com/jupyterhub/jupyterhub/pull/4663) ([@minrk](https://github.com/minrk))
- Use jupyterhub repository_owner in registry-overviews [#4642](https://github.com/jupyterhub/jupyterhub/pull/4642) ([@mathbunnyru](https://github.com/mathbunnyru), [@minrk](https://github.com/minrk))
- Publish to Docker Hub alongside Quay.io [#4641](https://github.com/jupyterhub/jupyterhub/pull/4641) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk))
- Add workflow to update registry overviews [#4634](https://github.com/jupyterhub/jupyterhub/pull/4634) ([@mathbunnyru](https://github.com/mathbunnyru), [@minrk](https://github.com/minrk))
- Set env.REGISTRY to be quay.io correctly [#4625](https://github.com/jupyterhub/jupyterhub/pull/4625) ([@yuvipanda](https://github.com/yuvipanda), [@manics](https://github.com/manics))
- FIx: typo in auth.py [#4619](https://github.com/jupyterhub/jupyterhub/pull/4619) ([@varundhand](https://github.com/varundhand), [@consideRatio](https://github.com/consideRatio))
- browser test: wait for token request to finish before reloading [#4618](https://github.com/jupyterhub/jupyterhub/pull/4618) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- try to improve reliability of test_external_proxy [#4617](https://github.com/jupyterhub/jupyterhub/pull/4617) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@lumberbot-app](https://github.com/lumberbot-app))
- test: ensure test server is added to proxy before talking to it [#4616](https://github.com/jupyterhub/jupyterhub/pull/4616) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@lumberbot-app](https://github.com/lumberbot-app))
- Move from dockerhub to quay.io [#4612](https://github.com/jupyterhub/jupyterhub/pull/4612) ([@yuvipanda](https://github.com/yuvipanda), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics), [@mathbunnyru](https://github.com/mathbunnyru))
- jsx: trade yarn for npm [#4598](https://github.com/jupyterhub/jupyterhub/pull/4598) ([@minrk](https://github.com/minrk), [@yuvipanda](https://github.com/yuvipanda), [@consideRatio](https://github.com/consideRatio))
- update nodesource installation in docker [#4597](https://github.com/jupyterhub/jupyterhub/pull/4597) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- skip linkcheck for linux.die.net [#4586](https://github.com/jupyterhub/jupyterhub/pull/4586) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- move oldest-dependencies to requirements.old [#4583](https://github.com/jupyterhub/jupyterhub/pull/4583) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- TST: apply lower-bound pins during install, rather than later [#4571](https://github.com/jupyterhub/jupyterhub/pull/4571) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- undeprecate JupyterHub.ip/port/base_url [#4564](https://github.com/jupyterhub/jupyterhub/pull/4564) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics), [@consideRatio](https://github.com/consideRatio), [@yuvipanda](https://github.com/yuvipanda), [@isaprykin](https://github.com/isaprykin))
- Fix typo in comment in spawner.py [#4546](https://github.com/jupyterhub/jupyterhub/pull/4546) ([@umka1332](https://github.com/umka1332), [@consideRatio](https://github.com/consideRatio))

#### Documentation improvements

- DOC: /share-codes/ url typo [#4816](https://github.com/jupyterhub/jupyterhub/pull/4816) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Update changelog for 5.0b2 [#4811](https://github.com/jupyterhub/jupyterhub/pull/4811) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- docs: fix internal reference typo [#4809](https://github.com/jupyterhub/jupyterhub/pull/4809) ([@consideRatio](https://github.com/consideRatio))
- document conditions for oauth_redirect_url more clearly [#4804](https://github.com/jupyterhub/jupyterhub/pull/4804) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Fix rest API djlint auto-formatting [#4796](https://github.com/jupyterhub/jupyterhub/pull/4796) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk))
- changelog for 5.0, add migration doc [#4792](https://github.com/jupyterhub/jupyterhub/pull/4792) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@krassowski](https://github.com/krassowski))
- doc: list/get token response is different from post [#4784](https://github.com/jupyterhub/jupyterhub/pull/4784) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk))
- Fix typo in docstring about Authenticator.blocked_users [#4769](https://github.com/jupyterhub/jupyterhub/pull/4769) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk))
- Officially adopt EffVer [#4743](https://github.com/jupyterhub/jupyterhub/pull/4743) ([@minrk](https://github.com/minrk), [@GeorgianaElena](https://github.com/GeorgianaElena), [@consideRatio](https://github.com/consideRatio), [@yuvipanda](https://github.com/yuvipanda), [@jacobtomlinson](https://github.com/jacobtomlinson))
- Consistently use minimum Python version in docs [#4741](https://github.com/jupyterhub/jupyterhub/pull/4741) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk))
- Bump required Python version in contributing setup to 3.8 [#4736](https://github.com/jupyterhub/jupyterhub/pull/4736) ([@krassowski](https://github.com/krassowski), [@minrk](https://github.com/minrk))
- services.md: idle-culler does not need admin [#4729](https://github.com/jupyterhub/jupyterhub/pull/4729) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk))
- Fix typo in the `rest-api.yml` [#4725](https://github.com/jupyterhub/jupyterhub/pull/4725) ([@aktech](https://github.com/aktech), [@minrk](https://github.com/minrk))
- remove broken link to old wiki [#4708](https://github.com/jupyterhub/jupyterhub/pull/4708) ([@rizz-sd](https://github.com/rizz-sd), [@minrk](https://github.com/minrk))
- Update allowed_users docstring [#4706](https://github.com/jupyterhub/jupyterhub/pull/4706) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Use redoc for REST API [#4700](https://github.com/jupyterhub/jupyterhub/pull/4700) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- clarify some points where users can disable security for their own servers [#4699](https://github.com/jupyterhub/jupyterhub/pull/4699) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Note that you can throw a 403 from authenticator methods [#4682](https://github.com/jupyterhub/jupyterhub/pull/4682) ([@yuvipanda](https://github.com/yuvipanda), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- pre_spawn_hook doc: make example generic to all spawners [#4678](https://github.com/jupyterhub/jupyterhub/pull/4678) ([@manics](https://github.com/manics), [@yuvipanda](https://github.com/yuvipanda), [@consideRatio](https://github.com/consideRatio))
- Add appropriate scope in examples/service-whoami-flask [#4676](https://github.com/jupyterhub/jupyterhub/pull/4676) ([@rschroll](https://github.com/rschroll), [@minrk](https://github.com/minrk))
- use $http_host in nginx proxy header [#4671](https://github.com/jupyterhub/jupyterhub/pull/4671) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- docs: Remove non-actionable step from developer setup [#4662](https://github.com/jupyterhub/jupyterhub/pull/4662) ([@yuvipanda](https://github.com/yuvipanda), [@minrk](https://github.com/minrk))
- ETHZ added to references in documentation [#4638](https://github.com/jupyterhub/jupyterhub/pull/4638) ([@BenGig](https://github.com/BenGig), [@minrk](https://github.com/minrk))
- Authenticator reference doc: update authenticate return [#4633](https://github.com/jupyterhub/jupyterhub/pull/4633) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk))
- doc: Add the include_stopped_server field to the /users/name interface [#4627](https://github.com/jupyterhub/jupyterhub/pull/4627) ([@eeeeeeeason](https://github.com/eeeeeeeason), [@minrk](https://github.com/minrk))
- Remove links to okpy from docs [#4603](https://github.com/jupyterhub/jupyterhub/pull/4603) ([@yuvipanda](https://github.com/yuvipanda), [@consideRatio](https://github.com/consideRatio))
- Change `db_url` schema in docs from `postgres` to `postgresql` [#4602](https://github.com/jupyterhub/jupyterhub/pull/4602) ([@johncf](https://github.com/johncf), [@yuvipanda](https://github.com/yuvipanda))
- add sirepo to gallery [#4568](https://github.com/jupyterhub/jupyterhub/pull/4568) ([@LexiJess](https://github.com/LexiJess), [@minrk](https://github.com/minrk))
- undeprecate JupyterHub.ip/port/base_url [#4564](https://github.com/jupyterhub/jupyterhub/pull/4564) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics), [@consideRatio](https://github.com/consideRatio), [@yuvipanda](https://github.com/yuvipanda), [@isaprykin](https://github.com/isaprykin))
- Remove broken link to BIDS video [#4558](https://github.com/jupyterhub/jupyterhub/pull/4558) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- add some more service credential docs [#4556](https://github.com/jupyterhub/jupyterhub/pull/4556) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Small fixes to services docs [#4552](https://github.com/jupyterhub/jupyterhub/pull/4552) ([@consideRatio](https://github.com/consideRatio), [@yuvipanda](https://github.com/yuvipanda), [@minrk](https://github.com/minrk))
- Fix external-oauth example jupyterhub_config.py [#4550](https://github.com/jupyterhub/jupyterhub/pull/4550) ([@yuvipanda](https://github.com/yuvipanda), [@minrk](https://github.com/minrk))
- Document `oauth_client_id` must start with service- [#4549](https://github.com/jupyterhub/jupyterhub/pull/4549) ([@yuvipanda](https://github.com/yuvipanda), [@consideRatio](https://github.com/consideRatio))
- Mention NomadSpawner [#4536](https://github.com/jupyterhub/jupyterhub/pull/4536) ([@mxab](https://github.com/mxab), [@minrk](https://github.com/minrk))
- Rename parameter for post_auth_hook to be clearer [#4511](https://github.com/jupyterhub/jupyterhub/pull/4511) ([@yuvipanda](https://github.com/yuvipanda), [@minrk](https://github.com/minrk))
- Documentation for RTC for JupyterLab >= 4.0 [#4508](https://github.com/jupyterhub/jupyterhub/pull/4508) ([@lrlunin](https://github.com/lrlunin), [@minrk](https://github.com/minrk))

#### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2023-08-10&to=2024-05-24&type=c))

@Achele ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AAchele+updated%3A2023-08-10..2024-05-24&type=Issues)) | @akashthedeveloper ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aakashthedeveloper+updated%3A2023-08-10..2024-05-24&type=Issues)) | @akhmerov ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aakhmerov+updated%3A2023-08-10..2024-05-24&type=Issues)) | @aktech ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aaktech+updated%3A2023-08-10..2024-05-24&type=Issues)) | @balajialg ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abalajialg+updated%3A2023-08-10..2024-05-24&type=Issues)) | @BenGig ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ABenGig+updated%3A2023-08-10..2024-05-24&type=Issues)) | @BhavyaT-135 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ABhavyaT-135+updated%3A2023-08-10..2024-05-24&type=Issues)) | @bl-aire ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abl-aire+updated%3A2023-08-10..2024-05-24&type=Issues)) | @blink1073 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ablink1073+updated%3A2023-08-10..2024-05-24&type=Issues)) | @cccs-nik ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acccs-nik+updated%3A2023-08-10..2024-05-24&type=Issues)) | @consideRatio ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2023-08-10..2024-05-24&type=Issues)) | @danilopeixoto ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adanilopeixoto+updated%3A2023-08-10..2024-05-24&type=Issues)) | @davidbrochart ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adavidbrochart+updated%3A2023-08-10..2024-05-24&type=Issues)) | @diocas ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adiocas+updated%3A2023-08-10..2024-05-24&type=Issues)) | @echarles ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aecharles+updated%3A2023-08-10..2024-05-24&type=Issues)) | @eeeeeeeason ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aeeeeeeeason+updated%3A2023-08-10..2024-05-24&type=Issues)) | @fcollonval ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Afcollonval+updated%3A2023-08-10..2024-05-24&type=Issues)) | @GeorgianaElena ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AGeorgianaElena+updated%3A2023-08-10..2024-05-24&type=Issues)) | @I-Am-D-B ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AI-Am-D-B+updated%3A2023-08-10..2024-05-24&type=Issues)) | @isaprykin ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aisaprykin+updated%3A2023-08-10..2024-05-24&type=Issues)) | @jabbera ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajabbera+updated%3A2023-08-10..2024-05-24&type=Issues)) | @jacobtomlinson ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajacobtomlinson+updated%3A2023-08-10..2024-05-24&type=Issues)) | @jakirkham ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajakirkham+updated%3A2023-08-10..2024-05-24&type=Issues)) | @johncf ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajohncf+updated%3A2023-08-10..2024-05-24&type=Issues)) | @johnpmayer ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajohnpmayer+updated%3A2023-08-10..2024-05-24&type=Issues)) | @jrdnbradford ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajrdnbradford+updated%3A2023-08-10..2024-05-24&type=Issues)) | @krassowski ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akrassowski+updated%3A2023-08-10..2024-05-24&type=Issues)) | @kreuzert ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akreuzert+updated%3A2023-08-10..2024-05-24&type=Issues)) | @ktaletsk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aktaletsk+updated%3A2023-08-10..2024-05-24&type=Issues)) | @kzgrzendek ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akzgrzendek+updated%3A2023-08-10..2024-05-24&type=Issues)) | @lahwaacz ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Alahwaacz+updated%3A2023-08-10..2024-05-24&type=Issues)) | @LexiJess ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ALexiJess+updated%3A2023-08-10..2024-05-24&type=Issues)) | @lrlunin ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Alrlunin+updated%3A2023-08-10..2024-05-24&type=Issues)) | @lumberbot-app ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Alumberbot-app+updated%3A2023-08-10..2024-05-24&type=Issues)) | @mahendrapaipuri ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amahendrapaipuri+updated%3A2023-08-10..2024-05-24&type=Issues)) | @manics ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2023-08-10..2024-05-24&type=Issues)) | @marcwit ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amarcwit+updated%3A2023-08-10..2024-05-24&type=Issues)) | @mathbunnyru ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amathbunnyru+updated%3A2023-08-10..2024-05-24&type=Issues)) | @mbiette ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ambiette+updated%3A2023-08-10..2024-05-24&type=Issues)) | @MetRonnie ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AMetRonnie+updated%3A2023-08-10..2024-05-24&type=Issues)) | @minrk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2023-08-10..2024-05-24&type=Issues)) | @mxab ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amxab+updated%3A2023-08-10..2024-05-24&type=Issues)) | @nreith ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Anreith+updated%3A2023-08-10..2024-05-24&type=Issues)) | @Ph0tonic ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3APh0tonic+updated%3A2023-08-10..2024-05-24&type=Issues)) | @rcthomas ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arcthomas+updated%3A2023-08-10..2024-05-24&type=Issues)) | @rizz-sd ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arizz-sd+updated%3A2023-08-10..2024-05-24&type=Issues)) | @rschroll ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arschroll+updated%3A2023-08-10..2024-05-24&type=Issues)) | @ryanlovett ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aryanlovett+updated%3A2023-08-10..2024-05-24&type=Issues)) | @sgaist ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asgaist+updated%3A2023-08-10..2024-05-24&type=Issues)) | @shubham0473 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ashubham0473+updated%3A2023-08-10..2024-05-24&type=Issues)) | @Temidayo32 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ATemidayo32+updated%3A2023-08-10..2024-05-24&type=Issues)) | @uellue ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Auellue+updated%3A2023-08-10..2024-05-24&type=Issues)) | @umka1332 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aumka1332+updated%3A2023-08-10..2024-05-24&type=Issues)) | @varundhand ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Avarundhand+updated%3A2023-08-10..2024-05-24&type=Issues)) | @willingc ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awillingc+updated%3A2023-08-10..2024-05-24&type=Issues)) | @yuvipanda ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2023-08-10..2024-05-24&type=Issues))

## 4.1

### 4.1.6 - 2024-07-31

4.1.6 is a **security release**, fixing [CVE-2024-41942].
All JupyterHub deployments are encouraged to upgrade,
but only those with users having the `admin:users` scope are affected.
The [full advisory][CVE-2024-41942] will be published 7 days after the release.

[CVE-2024-41942]: https://github.com/jupyterhub/jupyterhub/security/advisories/GHSA-9x4q-3gxw-849f

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/4.1.5...4.1.6))

### 4.1.5 - 2024-04-04

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/4.1.4...4.1.5))

#### Bugs fixed

- singleuser mixin: include check_xsrf_cookie in overrides [#4771](https://github.com/jupyterhub/jupyterhub/pull/4771) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2024-03-30&to=2024-04-04&type=c))

@consideRatio ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2024-03-30..2024-04-04&type=Issues)) | @manics ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2024-03-30..2024-04-04&type=Issues)) | @minrk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2024-03-30..2024-04-04&type=Issues))

### 4.1.4 - 2024-03-30

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/4.1.3...4.1.4))

#### Bugs fixed

- avoid xsrf check on navigate GET requests [#4759](https://github.com/jupyterhub/jupyterhub/pull/4759) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2024-03-26&to=2024-03-30&type=c))

@consideRatio ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2024-03-26..2024-03-30&type=Issues)) | @minrk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2024-03-26..2024-03-30&type=Issues))

### 4.1.3 - 2024-03-26

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/4.1.2...4.1.3))

#### Bugs fixed

- respect jupyter-server disable_check_xsrf setting [#4753](https://github.com/jupyterhub/jupyterhub/pull/4753) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2024-03-25&to=2024-03-26&type=c))

@consideRatio ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2024-03-25..2024-03-26&type=Issues)) | @minrk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2024-03-25..2024-03-26&type=Issues))

### 4.1.2 - 2024-03-25

4.1.2 fixes a regression in 4.1.0 affecting named servers.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/4.1.1...4.1.2))

#### Bugs fixed

- rework handling of multiple xsrf tokens [#4750](https://github.com/jupyterhub/jupyterhub/pull/4750) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2024-03-23&to=2024-03-25&type=c))

@consideRatio ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2024-03-23..2024-03-25&type=Issues)) | @minrk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2024-03-23..2024-03-25&type=Issues))

### 4.1.1 - 2024-03-23

4.1.1 fixes a compatibility regression in 4.1.0 for some extensions,
particularly jupyter-server-proxy.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/4.1.0...4.1.1))

#### Bugs fixed

- allow subclasses to override xsrf check [#4745](https://github.com/jupyterhub/jupyterhub/pull/4745) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2024-03-20&to=2024-03-23&type=c))

@consideRatio ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2024-03-20..2024-03-23&type=Issues)) | @minrk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2024-03-20..2024-03-23&type=Issues))

### 4.1.0 - 2024-03-20

JupyterHub 4.1 is a security release, fixing [CVE-2024-28233].
All JupyterHub deployments are encouraged to upgrade,
especially those with other user content on peer domains to JupyterHub.

As always, JupyterHub deployments are especially encouraged to enable per-user domains if protecting users from each other is a concern.

For more information on securely deploying JupyterHub, see the [web security documentation](explanation:security).

[CVE-2024-28233]: https://github.com/jupyterhub/jupyterhub/security/advisories/GHSA-7r3h-4ph8-w38g

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/4.0.2...4.1.0))

#### Enhancements made

- Backport PR #4628 on branch 4.x (Include LDAP groups in local spawner gids) [#4735](https://github.com/jupyterhub/jupyterhub/pull/4735) ([@minrk](https://github.com/minrk))
- Backport PR #4561 on branch 4.x (Improve debugging when waiting for servers) [#4714](https://github.com/jupyterhub/jupyterhub/pull/4714) ([@minrk](https://github.com/minrk))
- Backport PR #4563 on branch 4.x (only set 'domain' field on session-id cookie) [#4707](https://github.com/jupyterhub/jupyterhub/pull/4707) ([@minrk](https://github.com/minrk))

#### Bugs fixed

- Backport PR #4733 on branch 4.x (Catch ValueError while waiting for server to be reachable) [#4734](https://github.com/jupyterhub/jupyterhub/pull/4734) ([@minrk](https://github.com/minrk))
- Backport PR #4679 on branch 4.x (Unescape jinja username) [#4705](https://github.com/jupyterhub/jupyterhub/pull/4705) ([@minrk](https://github.com/minrk))
- Backport PR #4630: avoid setting unused oauth state cookies on API requests [#4697](https://github.com/jupyterhub/jupyterhub/pull/4697) ([@minrk](https://github.com/minrk))
- Backport PR #4632: simplify, avoid errors in parsing accept headers [#4696](https://github.com/jupyterhub/jupyterhub/pull/4696) ([@minrk](https://github.com/minrk))
- Backport PR #4677 on branch 4.x (Improve validation, docs for token.expires_in) [#4692](https://github.com/jupyterhub/jupyterhub/pull/4692) ([@minrk](https://github.com/minrk))
- Backport PR #4570 on branch 4.x (fix mutation of frozenset in scope intersection) [#4691](https://github.com/jupyterhub/jupyterhub/pull/4691) ([@minrk](https://github.com/minrk))
- Backport PR #4562 on branch 4.x (Use `user.stop` to cleanup spawners that stopped while Hub was down) [#4690](https://github.com/jupyterhub/jupyterhub/pull/4690) ([@minrk](https://github.com/minrk))
- Backport PR #4542 on branch 4.x (Fix include_stopped_servers in paginated next_url) [#4689](https://github.com/jupyterhub/jupyterhub/pull/4689) ([@minrk](https://github.com/minrk))
- Backport PR #4651 on branch 4.x (avoid attempting to patch removed IPythonHandler with notebook v7) [#4688](https://github.com/jupyterhub/jupyterhub/pull/4688) ([@minrk](https://github.com/minrk))
- Backport PR #4560 on branch 4.x (singleuser extension: persist token from ?token=... url in cookie) [#4687](https://github.com/jupyterhub/jupyterhub/pull/4687) ([@minrk](https://github.com/minrk))

#### Maintenance and upkeep improvements

- Backport quay.io publishing [#4698](https://github.com/jupyterhub/jupyterhub/pull/4698) ([@minrk](https://github.com/minrk))
- Backport PR #4617: try to improve reliability of test_external_proxy [#4695](https://github.com/jupyterhub/jupyterhub/pull/4695) ([@minrk](https://github.com/minrk))
- Backport PR #4618 on branch 4.x (browser test: wait for token request to finish before reloading) [#4694](https://github.com/jupyterhub/jupyterhub/pull/4694) ([@minrk](https://github.com/minrk))
- preparing 4.x branch [#4685](https://github.com/jupyterhub/jupyterhub/pull/4685) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2023-08-10&to=2024-03-19&type=c))

@Achele ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AAchele+updated%3A2023-08-10..2024-03-19&type=Issues)) | @akashthedeveloper ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aakashthedeveloper+updated%3A2023-08-10..2024-03-19&type=Issues)) | @balajialg ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abalajialg+updated%3A2023-08-10..2024-03-19&type=Issues)) | @BhavyaT-135 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ABhavyaT-135+updated%3A2023-08-10..2024-03-19&type=Issues)) | @blink1073 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ablink1073+updated%3A2023-08-10..2024-03-19&type=Issues)) | @consideRatio ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2023-08-10..2024-03-19&type=Issues)) | @fcollonval ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Afcollonval+updated%3A2023-08-10..2024-03-19&type=Issues)) | @I-Am-D-B ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AI-Am-D-B+updated%3A2023-08-10..2024-03-19&type=Issues)) | @jakirkham ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajakirkham+updated%3A2023-08-10..2024-03-19&type=Issues)) | @ktaletsk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aktaletsk+updated%3A2023-08-10..2024-03-19&type=Issues)) | @kzgrzendek ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akzgrzendek+updated%3A2023-08-10..2024-03-19&type=Issues)) | @lumberbot-app ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Alumberbot-app+updated%3A2023-08-10..2024-03-19&type=Issues)) | @manics ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2023-08-10..2024-03-19&type=Issues)) | @mbiette ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ambiette+updated%3A2023-08-10..2024-03-19&type=Issues)) | @minrk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2023-08-10..2024-03-19&type=Issues)) | @rcthomas ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arcthomas+updated%3A2023-08-10..2024-03-19&type=Issues)) | @ryanlovett ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aryanlovett+updated%3A2023-08-10..2024-03-19&type=Issues)) | @sgaist ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asgaist+updated%3A2023-08-10..2024-03-19&type=Issues)) | @shubham0473 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ashubham0473+updated%3A2023-08-10..2024-03-19&type=Issues)) | @Temidayo32 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ATemidayo32+updated%3A2023-08-10..2024-03-19&type=Issues)) | @willingc ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awillingc+updated%3A2023-08-10..2024-03-19&type=Issues)) | @yuvipanda ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2023-08-10..2024-03-19&type=Issues))

## 4.0

### 4.0.2 - 2023-08-10

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/4.0.1...4.0.2))

#### Enhancements made

- avoid counting failed requests to not-running servers as 'activity' [#4491](https://github.com/jupyterhub/jupyterhub/pull/4491) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- improve permission-denied errors for various cases [#4489](https://github.com/jupyterhub/jupyterhub/pull/4489) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Bugs fixed

- set root_dir when using singleuser extension [#4503](https://github.com/jupyterhub/jupyterhub/pull/4503) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- Allow setting custom log_function in tornado_settings in SingleUserServer [#4475](https://github.com/jupyterhub/jupyterhub/pull/4475) ([@grios-stratio](https://github.com/grios-stratio), [@minrk](https://github.com/minrk))

#### Documentation improvements

- doc: update notebook config URL [#4523](https://github.com/jupyterhub/jupyterhub/pull/4523) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- document how to use notebook v7 with jupyterhub [#4522](https://github.com/jupyterhub/jupyterhub/pull/4522) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))

#### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2023-06-08&to=2023-08-10&type=c))

@agelosnm ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aagelosnm+updated%3A2023-06-08..2023-08-10&type=Issues)) | @consideRatio ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2023-06-08..2023-08-10&type=Issues)) | @diocas ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adiocas+updated%3A2023-06-08..2023-08-10&type=Issues)) | @grios-stratio ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Agrios-stratio+updated%3A2023-06-08..2023-08-10&type=Issues)) | @jhgoebbert ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajhgoebbert+updated%3A2023-06-08..2023-08-10&type=Issues)) | @jtpio ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajtpio+updated%3A2023-06-08..2023-08-10&type=Issues)) | @kosmonavtus ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akosmonavtus+updated%3A2023-06-08..2023-08-10&type=Issues)) | @kreuzert ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akreuzert+updated%3A2023-06-08..2023-08-10&type=Issues)) | @manics ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2023-06-08..2023-08-10&type=Issues)) | @martinRenou ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AmartinRenou+updated%3A2023-06-08..2023-08-10&type=Issues)) | @minrk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2023-06-08..2023-08-10&type=Issues)) | @opoplawski ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aopoplawski+updated%3A2023-06-08..2023-08-10&type=Issues)) | @Ph0tonic ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3APh0tonic+updated%3A2023-06-08..2023-08-10&type=Issues)) | @sgaist ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asgaist+updated%3A2023-06-08..2023-08-10&type=Issues)) | @trungleduc ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atrungleduc+updated%3A2023-06-08..2023-08-10&type=Issues)) | @yuvipanda ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2023-06-08..2023-08-10&type=Issues))

### 4.0.1 - 2023-06-08

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/4.0.0...4.0.1))

#### Enhancements made

- Delete server button on admin page [#4457](https://github.com/jupyterhub/jupyterhub/pull/4457) ([@diocas](https://github.com/diocas), [@minrk](https://github.com/minrk))

#### Bugs fixed

- Abort informatively on unrecognized CLI options [#4467](https://github.com/jupyterhub/jupyterhub/pull/4467) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Add xsrf to custom_html template context [#4464](https://github.com/jupyterhub/jupyterhub/pull/4464) ([@opoplawski](https://github.com/opoplawski), [@minrk](https://github.com/minrk))
- preserve CLI > env priority config in jupyterhub-singleuser extension [#4451](https://github.com/jupyterhub/jupyterhub/pull/4451) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@timeu](https://github.com/timeu), [@rcthomas](https://github.com/rcthomas))

#### Maintenance and upkeep improvements

- Fix link to collaboration accounts doc in example [#4448](https://github.com/jupyterhub/jupyterhub/pull/4448) ([@minrk](https://github.com/minrk))
- Remove Dockerfile.alpine [#4444](https://github.com/jupyterhub/jupyterhub/pull/4444) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk))
- Update jsx dependencies as much as possible [#4443](https://github.com/jupyterhub/jupyterhub/pull/4443) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Remove unused admin JS code [#4438](https://github.com/jupyterhub/jupyterhub/pull/4438) ([@yuvipanda](https://github.com/yuvipanda), [@minrk](https://github.com/minrk))
- Finish migrating browser tests from selenium to playwright [#4435](https://github.com/jupyterhub/jupyterhub/pull/4435) ([@mouse1203](https://github.com/mouse1203), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Migrate some tests from selenium to playwright [#4431](https://github.com/jupyterhub/jupyterhub/pull/4431) ([@mouse1203](https://github.com/mouse1203), [@minrk](https://github.com/minrk))
- Begin setup of playwright tests [#4420](https://github.com/jupyterhub/jupyterhub/pull/4420) ([@mouse1203](https://github.com/mouse1203), [@minrk](https://github.com/minrk), [@manics](https://github.com/manics))

#### Documentation improvements

- Reorder token request docs [#4463](https://github.com/jupyterhub/jupyterhub/pull/4463) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- 'servers' should be a dict of dicts, not a list of dicts in rest-api.yml [#4458](https://github.com/jupyterhub/jupyterhub/pull/4458) ([@tfmark](https://github.com/tfmark), [@minrk](https://github.com/minrk))
- Config reference: link to nicer(?) API docs first [#4456](https://github.com/jupyterhub/jupyterhub/pull/4456) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Add CERN to Gallery of JupyterHub Deployments [#4454](https://github.com/jupyterhub/jupyterhub/pull/4454) ([@goseind](https://github.com/goseind), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Fix "Thanks" typo. [#4441](https://github.com/jupyterhub/jupyterhub/pull/4441) ([@ryanlovett](https://github.com/ryanlovett), [@minrk](https://github.com/minrk))
- add HUNT into research institutions [#4432](https://github.com/jupyterhub/jupyterhub/pull/4432) ([@matuskosut](https://github.com/matuskosut), [@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- docs: fix missing redirects for api to reference/api [#4429](https://github.com/jupyterhub/jupyterhub/pull/4429) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- update sharing faq for 2023 [#4428](https://github.com/jupyterhub/jupyterhub/pull/4428) ([@minrk](https://github.com/minrk))
- Fix some public URL links within the docs [#4427](https://github.com/jupyterhub/jupyterhub/pull/4427) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- add upgrade note for 4.0 to changelog [#4426](https://github.com/jupyterhub/jupyterhub/pull/4426) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2023-04-20&to=2023-06-07&type=c))

@consideRatio ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2023-04-20..2023-06-07&type=Issues)) | @diocas ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adiocas+updated%3A2023-04-20..2023-06-07&type=Issues)) | @echarles ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aecharles+updated%3A2023-04-20..2023-06-07&type=Issues)) | @goseind ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Agoseind+updated%3A2023-04-20..2023-06-07&type=Issues)) | @hsadia538 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ahsadia538+updated%3A2023-04-20..2023-06-07&type=Issues)) | @mahamtariq58 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amahamtariq58+updated%3A2023-04-20..2023-06-07&type=Issues)) | @manics ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2023-04-20..2023-06-07&type=Issues)) | @matuskosut ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amatuskosut+updated%3A2023-04-20..2023-06-07&type=Issues)) | @minrk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2023-04-20..2023-06-07&type=Issues)) | @mouse1203 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amouse1203+updated%3A2023-04-20..2023-06-07&type=Issues)) | @opoplawski ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aopoplawski+updated%3A2023-04-20..2023-06-07&type=Issues)) | @rcthomas ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arcthomas+updated%3A2023-04-20..2023-06-07&type=Issues)) | @ryanlovett ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aryanlovett+updated%3A2023-04-20..2023-06-07&type=Issues)) | @tfmark ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atfmark+updated%3A2023-04-20..2023-06-07&type=Issues)) | @timeu ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atimeu+updated%3A2023-04-20..2023-06-07&type=Issues)) | @yuvipanda ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2023-04-20..2023-06-07&type=Issues))

### 4.0.0 - 2023-04-20

4.0 is a major release, but a small one.

:::{admonition} Upgrade note

Upgrading from 3.1 to 4.0 should require no additional action beyond running `jupyterhub --upgrade-db` to upgrade the database schema after upgrading the package version.
It is otherwise a regular jupyterhub [upgrade](howto:upgrading-jupyterhub).
:::

There are three major changes that _should_ be invisible to most users:

1. Groups can now have 'properties', editable via the admin page, which can be used by Spawners for their operations.
   This requires a db schema upgrade, so remember to [**backup and upgrade your database**](howto:upgrading-jupyterhub)!
2. Often-problematic header-based checks for cross-site requests have been replaces with more standard use of XSRF tokens.
   Most folks shouldn't notice this change, but if "Blocking Cross Origin API request" has been giving you headaches, this should be much improved.
3. Improved support for Jupyter Server 2.0 by reimplementing `jupyterhub-singleuser` as a standard _server extension_.
   This mode is used by default with Jupyter Server >=2.0.
   Again, this should be an implementation detail to most, but it's a big change under the hood.
   If you have issues, please let us know and you can opt-out by setting `JUPYTERHUB_SINGLEUSER_EXTENSION=0` in your single-user environment.

In addition to these, thanks to contributions from this years Outreachy interns, we have reorganized the documentation according to [diataxis](https://diataxis.fr), improved accessibility of JupyterHub pages, and improved testing.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/3.1.0...4.0.0))

#### API and Breaking Changes

- require sqlalchemy 1.4 [#4319](https://github.com/jupyterhub/jupyterhub/pull/4319) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- Use XSRF tokens for cross-site checks [#4032](https://github.com/jupyterhub/jupyterhub/pull/4032) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@julietKiloRomeo](https://github.com/julietKiloRomeo))

#### New features added

- add Spawner.server_token_scopes config [#4400](https://github.com/jupyterhub/jupyterhub/pull/4400) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Make singleuser server-extension default [#4354](https://github.com/jupyterhub/jupyterhub/pull/4354) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- singleuser auth as server extension [#3888](https://github.com/jupyterhub/jupyterhub/pull/3888) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Dynamic table for changing customizable properties of groups [#3651](https://github.com/jupyterhub/jupyterhub/pull/3651) ([@vladfreeze](https://github.com/vladfreeze), [@minrk](https://github.com/minrk), [@naatebarber](https://github.com/naatebarber), [@manics](https://github.com/manics))

#### Enhancements made

- admin page: improve display of long lists (groups, etc.) [#4417](https://github.com/jupyterhub/jupyterhub/pull/4417) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk), [@ryanlovett](https://github.com/ryanlovett))
- add a few more buckets for server_spawn_duration_seconds [#4352](https://github.com/jupyterhub/jupyterhub/pull/4352) ([@shaneknapp](https://github.com/shaneknapp), [@yuvipanda](https://github.com/yuvipanda))
- Improve contrast on muted text [#4326](https://github.com/jupyterhub/jupyterhub/pull/4326) ([@bl-aire](https://github.com/bl-aire), [@minrk](https://github.com/minrk))
- Standardize styling on input fields by moving common form CSS to page.less [#4294](https://github.com/jupyterhub/jupyterhub/pull/4294) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Bugs fixed

- make sure named server URLs include trailing slash [#4402](https://github.com/jupyterhub/jupyterhub/pull/4402) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- fix inclusion of singleuser/templates/page.html in wheel [#4387](https://github.com/jupyterhub/jupyterhub/pull/4387) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk))
- exponential_backoff: preserve jitter when max_wait is reached [#4383](https://github.com/jupyterhub/jupyterhub/pull/4383) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- admin panel: fix condition for start/stop buttons on user servers [#4365](https://github.com/jupyterhub/jupyterhub/pull/4365) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- avoid logging error when browsers send invalid cookies [#4356](https://github.com/jupyterhub/jupyterhub/pull/4356) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics), [@consideRatio](https://github.com/consideRatio))
- test and fix deprecated load_groups list [#4299](https://github.com/jupyterhub/jupyterhub/pull/4299) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- Fix formatting of load_groups help string [#4295](https://github.com/jupyterhub/jupyterhub/pull/4295) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Fix skipped heading level across pages [#4290](https://github.com/jupyterhub/jupyterhub/pull/4290) ([@bl-aire](https://github.com/bl-aire), [@minrk](https://github.com/minrk))
- Fix reoccurring accessibility issues in JupyterHub's pages [#4274](https://github.com/jupyterhub/jupyterhub/pull/4274) ([@bl-aire](https://github.com/bl-aire), [@minrk](https://github.com/minrk))
- Remove remnants of unused jupyterhub-services cookie [#4258](https://github.com/jupyterhub/jupyterhub/pull/4258) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Maintenance and upkeep improvements

- add remaining redirects for docs reorg [#4423](https://github.com/jupyterhub/jupyterhub/pull/4423) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Disable dev traitlets [#4419](https://github.com/jupyterhub/jupyterhub/pull/4419) ([@manics](https://github.com/manics), [@consideRatio](https://github.com/consideRatio))
- dependabot: rename to .yaml [#4409](https://github.com/jupyterhub/jupyterhub/pull/4409) ([@consideRatio](https://github.com/consideRatio))
- dependabot: fix syntax error of not using quotes for ##:## [#4408](https://github.com/jupyterhub/jupyterhub/pull/4408) ([@consideRatio](https://github.com/consideRatio))
- dependabot: monthly updates of github actions [#4403](https://github.com/jupyterhub/jupyterhub/pull/4403) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk))
- Refresh 4.0 changelog [#4396](https://github.com/jupyterhub/jupyterhub/pull/4396) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Reduce size of jupyterhub image [#4394](https://github.com/jupyterhub/jupyterhub/pull/4394) ([@alekseyolg](https://github.com/alekseyolg), [@minrk](https://github.com/minrk))
- Selenium: updating test_oauth_page [#4393](https://github.com/jupyterhub/jupyterhub/pull/4393) ([@mouse1203](https://github.com/mouse1203), [@minrk](https://github.com/minrk))
- avoid warning on engine_connect listener [#4392](https://github.com/jupyterhub/jupyterhub/pull/4392) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- remove pin from singleuser [#4379](https://github.com/jupyterhub/jupyterhub/pull/4379) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@mathbunnyru](https://github.com/mathbunnyru))
- temporary fix: pin base-notebook tag [#4348](https://github.com/jupyterhub/jupyterhub/pull/4348) ([@minrk](https://github.com/minrk))
- simplify some async fixtures [#4332](https://github.com/jupyterhub/jupyterhub/pull/4332) ([@minrk](https://github.com/minrk), [@GeorgianaElena](https://github.com/GeorgianaElena), [@Sheila-nk](https://github.com/Sheila-nk))
- Selenium: adding new cases that covered Admin UI page [#4328](https://github.com/jupyterhub/jupyterhub/pull/4328) ([@mouse1203](https://github.com/mouse1203), [@minrk](https://github.com/minrk))
- also ignore sqlite backups [#4327](https://github.com/jupyterhub/jupyterhub/pull/4327) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- pre-commit: bump isort [#4325](https://github.com/jupyterhub/jupyterhub/pull/4325) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Remove no longer relevant notice in readme [#4324](https://github.com/jupyterhub/jupyterhub/pull/4324) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk))
- Fix the oauthenticator docs api links [#4304](https://github.com/jupyterhub/jupyterhub/pull/4304) ([@GeorgianaElena](https://github.com/GeorgianaElena), [@minrk](https://github.com/minrk))
- Selenium testing: adding new case covered the authorisation page [#4298](https://github.com/jupyterhub/jupyterhub/pull/4298) ([@mouse1203](https://github.com/mouse1203), [@minrk](https://github.com/minrk))
- docs: fix linkcheck in gallery [#4297](https://github.com/jupyterhub/jupyterhub/pull/4297) ([@minrk](https://github.com/minrk))
- Refactored selenium tests for improved readability [#4278](https://github.com/jupyterhub/jupyterhub/pull/4278) ([@mouse1203](https://github.com/mouse1203), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- remove deprecated import of pipes.quote [#4273](https://github.com/jupyterhub/jupyterhub/pull/4273) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- only run testing config on localhost [#4271](https://github.com/jupyterhub/jupyterhub/pull/4271) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- pre-commit: autoupdate monthly [#4268](https://github.com/jupyterhub/jupyterhub/pull/4268) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@GeorgianaElena](https://github.com/GeorgianaElena), [@betatim](https://github.com/betatim))
- remove unnecessary actions for firefox/geckodriver [#4264](https://github.com/jupyterhub/jupyterhub/pull/4264) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- docs: refresh Makefile/make.bat [#4256](https://github.com/jupyterhub/jupyterhub/pull/4256) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk))
- Test docs, links on CI [#4251](https://github.com/jupyterhub/jupyterhub/pull/4251) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- maint: fix detail when removing support for py36 [#4248](https://github.com/jupyterhub/jupyterhub/pull/4248) ([@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- more selenium test cases [#4207](https://github.com/jupyterhub/jupyterhub/pull/4207) ([@mouse1203](https://github.com/mouse1203), [@minrk](https://github.com/minrk))

#### Documentation improvements

- Fix variable spelling. [#4398](https://github.com/jupyterhub/jupyterhub/pull/4398) ([@ryanlovett](https://github.com/ryanlovett), [@manics](https://github.com/manics))
- Remove bracket around link text without address [#4416](https://github.com/jupyterhub/jupyterhub/pull/4416) ([@crazytan](https://github.com/crazytan), [@minrk](https://github.com/minrk))
- add some more detail and examples to database doc [#4399](https://github.com/jupyterhub/jupyterhub/pull/4399) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Add emphasis about role loading and hub restarts. [#4390](https://github.com/jupyterhub/jupyterhub/pull/4390) ([@ryanlovett](https://github.com/ryanlovett), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Re-enable links to REST API [#4386](https://github.com/jupyterhub/jupyterhub/pull/4386) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- reduce nested hierarchy in docs organization [#4377](https://github.com/jupyterhub/jupyterhub/pull/4377) ([@alwasega](https://github.com/alwasega), [@minrk](https://github.com/minrk))
- changelog for 4.0 beta [#4375](https://github.com/jupyterhub/jupyterhub/pull/4375) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Getting started link broken [#4374](https://github.com/jupyterhub/jupyterhub/pull/4374) ([@3coins](https://github.com/3coins), [@minrk](https://github.com/minrk))
- add collaboration accounts tutorial [#4373](https://github.com/jupyterhub/jupyterhub/pull/4373) ([@minrk](https://github.com/minrk), [@fperez](https://github.com/fperez), [@ryanlovett](https://github.com/ryanlovett))
- Updated the top-level index file [#4368](https://github.com/jupyterhub/jupyterhub/pull/4368) ([@alwasega](https://github.com/alwasega), [@sgibson91](https://github.com/sgibson91))
- JupyterHub sphinx theme [#4363](https://github.com/jupyterhub/jupyterhub/pull/4363) ([@minrk](https://github.com/minrk), [@choldgraf](https://github.com/choldgraf))
- Remove PDF links from README.md [#4358](https://github.com/jupyterhub/jupyterhub/pull/4358) ([@pnasrat](https://github.com/pnasrat), [@manics](https://github.com/manics))
- add singleuser explanation doc [#4357](https://github.com/jupyterhub/jupyterhub/pull/4357) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Updates to the documentation Contribution section [#4355](https://github.com/jupyterhub/jupyterhub/pull/4355) ([@alwasega](https://github.com/alwasega), [@sgibson91](https://github.com/sgibson91), [@minrk](https://github.com/minrk))
- Restructured references section of the docs [#4343](https://github.com/jupyterhub/jupyterhub/pull/4343) ([@alwasega](https://github.com/alwasega), [@minrk](https://github.com/minrk), [@sgibson91](https://github.com/sgibson91))
- Document use of pytest-asyncio in JupyterHub test suite [#4341](https://github.com/jupyterhub/jupyterhub/pull/4341) ([@Sheila-nk](https://github.com/Sheila-nk), [@minrk](https://github.com/minrk), [@alwasega](https://github.com/alwasega))
- Moved Explanation/Background files [#4340](https://github.com/jupyterhub/jupyterhub/pull/4340) ([@alwasega](https://github.com/alwasega), [@sgibson91](https://github.com/sgibson91), [@minrk](https://github.com/minrk))
- Moved last set of Tutorials [#4338](https://github.com/jupyterhub/jupyterhub/pull/4338) ([@alwasega](https://github.com/alwasega), [@sgibson91](https://github.com/sgibson91))
- fix a couple ref links in changelog [#4334](https://github.com/jupyterhub/jupyterhub/pull/4334) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Added rediraffe using auto redirect builder [#4331](https://github.com/jupyterhub/jupyterhub/pull/4331) ([@alwasega](https://github.com/alwasega), [@sgibson91](https://github.com/sgibson91), [@GeorgianaElena](https://github.com/GeorgianaElena), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- Backport PR #4316 on branch 3.x (changelog for 3.1.1) [#4318](https://github.com/jupyterhub/jupyterhub/pull/4318) ([@minrk](https://github.com/minrk))
- changelog for 3.1.1 [#4316](https://github.com/jupyterhub/jupyterhub/pull/4316) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Moved second half of HowTo documentation [#4314](https://github.com/jupyterhub/jupyterhub/pull/4314) ([@alwasega](https://github.com/alwasega), [@sgibson91](https://github.com/sgibson91), [@minrk](https://github.com/minrk))
- Moved first half of HowTo documentation [#4311](https://github.com/jupyterhub/jupyterhub/pull/4311) ([@alwasega](https://github.com/alwasega), [@sgibson91](https://github.com/sgibson91), [@minrk](https://github.com/minrk))
- number agreement in authenticators-users-basics [#4309](https://github.com/jupyterhub/jupyterhub/pull/4309) ([@TaofeeqatDev](https://github.com/TaofeeqatDev), [@minrk](https://github.com/minrk))
- transferred docs to the FAQ folder [#4307](https://github.com/jupyterhub/jupyterhub/pull/4307) ([@alwasega](https://github.com/alwasega), [@sgibson91](https://github.com/sgibson91), [@minrk](https://github.com/minrk), [@GeorgianaElena](https://github.com/GeorgianaElena))
- Added docs to the folder [#4305](https://github.com/jupyterhub/jupyterhub/pull/4305) ([@alwasega](https://github.com/alwasega), [@sgibson91](https://github.com/sgibson91), [@minrk](https://github.com/minrk))
- Created folders to house the restructured documentation [#4301](https://github.com/jupyterhub/jupyterhub/pull/4301) ([@alwasega](https://github.com/alwasega), [@sgibson91](https://github.com/sgibson91), [@minrk](https://github.com/minrk), [@manics](https://github.com/manics), [@GeorgianaElena](https://github.com/GeorgianaElena))
- expand database docs [#4292](https://github.com/jupyterhub/jupyterhub/pull/4292) ([@minrk](https://github.com/minrk), [@GeorgianaElena](https://github.com/GeorgianaElena), [@ajpower](https://github.com/ajpower), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics), [@sgibson91](https://github.com/sgibson91))
- added note on `Spawner.name_template` setting [#4288](https://github.com/jupyterhub/jupyterhub/pull/4288) ([@stevejpurves](https://github.com/stevejpurves), [@minrk](https://github.com/minrk))
- Document JUPYTER_PREFER_ENV_PATH=0 for shared user environments [#4269](https://github.com/jupyterhub/jupyterhub/pull/4269) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- set max depth on api/index toctree [#4259](https://github.com/jupyterhub/jupyterhub/pull/4259) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- fix bracket typo in capacity figures [#4250](https://github.com/jupyterhub/jupyterhub/pull/4250) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- convert remaining rst files to myst [#4249](https://github.com/jupyterhub/jupyterhub/pull/4249) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- doc: fix formatting of spawner env-vars [#4245](https://github.com/jupyterhub/jupyterhub/pull/4245) ([@manics](https://github.com/manics), [@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk))

#### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2022-12-05&to=2023-04-20&type=c))

@3coins ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3A3coins+updated%3A2022-12-05..2023-04-20&type=Issues)) | @ajcollett ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aajcollett+updated%3A2022-12-05..2023-04-20&type=Issues)) | @ajpower ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aajpower+updated%3A2022-12-05..2023-04-20&type=Issues)) | @alekseyolg ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aalekseyolg+updated%3A2022-12-05..2023-04-20&type=Issues)) | @alwasega ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aalwasega+updated%3A2022-12-05..2023-04-20&type=Issues)) | @betatim ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abetatim+updated%3A2022-12-05..2023-04-20&type=Issues)) | @bl-aire ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abl-aire+updated%3A2022-12-05..2023-04-20&type=Issues)) | @choldgraf ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acholdgraf+updated%3A2022-12-05..2023-04-20&type=Issues)) | @consideRatio ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2022-12-05..2023-04-20&type=Issues)) | @crazytan ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acrazytan+updated%3A2022-12-05..2023-04-20&type=Issues)) | @dependabot ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adependabot+updated%3A2022-12-05..2023-04-20&type=Issues)) | @fperez ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Afperez+updated%3A2022-12-05..2023-04-20&type=Issues)) | @GeorgianaElena ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AGeorgianaElena+updated%3A2022-12-05..2023-04-20&type=Issues)) | @julietKiloRomeo ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AjulietKiloRomeo+updated%3A2022-12-05..2023-04-20&type=Issues)) | @ktaletsk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aktaletsk+updated%3A2022-12-05..2023-04-20&type=Issues)) | @manics ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2022-12-05..2023-04-20&type=Issues)) | @mathbunnyru ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amathbunnyru+updated%3A2022-12-05..2023-04-20&type=Issues)) | @meeseeksdev ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ameeseeksdev+updated%3A2022-12-05..2023-04-20&type=Issues)) | @meeseeksmachine ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ameeseeksmachine+updated%3A2022-12-05..2023-04-20&type=Issues)) | @minrk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2022-12-05..2023-04-20&type=Issues)) | @mouse1203 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amouse1203+updated%3A2022-12-05..2023-04-20&type=Issues)) | @naatebarber ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Anaatebarber+updated%3A2022-12-05..2023-04-20&type=Issues)) | @pnasrat ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apnasrat+updated%3A2022-12-05..2023-04-20&type=Issues)) | @pre-commit-ci ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apre-commit-ci+updated%3A2022-12-05..2023-04-20&type=Issues)) | @ryanlovett ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aryanlovett+updated%3A2022-12-05..2023-04-20&type=Issues)) | @sgibson91 ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asgibson91+updated%3A2022-12-05..2023-04-20&type=Issues)) | @shaneknapp ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ashaneknapp+updated%3A2022-12-05..2023-04-20&type=Issues)) | @Sheila-nk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ASheila-nk+updated%3A2022-12-05..2023-04-20&type=Issues)) | @stevejpurves ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Astevejpurves+updated%3A2022-12-05..2023-04-20&type=Issues)) | @TaofeeqatDev ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ATaofeeqatDev+updated%3A2022-12-05..2023-04-20&type=Issues)) | @vladfreeze ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Avladfreeze+updated%3A2022-12-05..2023-04-20&type=Issues)) | @yuvipanda ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2022-12-05..2023-04-20&type=Issues))

## 3.1

### 3.1.1 - 2023-01-27

3.1.1 has only tiny bugfixes, enabling compatibility with the latest sqlalchemy 2.0 release, and fixing some metadata files that were not being included in wheel installs.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/3.1.0...3.1.1))

#### Bugs fixed

- Backport PR #4303 on branch 3.x: make sure event-schemas are installed [#4317](https://github.com/jupyterhub/jupyterhub/pull/4317) ([@minrk](https://github.com/minrk))
- Backport PR #4302 on branch 3.x: sqlalchemy 2 compatibility [#4315](https://github.com/jupyterhub/jupyterhub/pull/4315) ([@minrk](https://github.com/minrk))

### 3.1.0 - 2022-12-05

3.1.0 is a small release, fixing various bugs and introducing some small new features and metrics.
See more details below.

Thanks to many Outreachy applicants for significantly improving our documentation!
This release fixes a problem in the jupyterhub/jupyterhub docker image,
where the admin page could be empty.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/3.0.0...3.1.0))

#### New features added

- Add active users prometheus metrics [#4214](https://github.com/jupyterhub/jupyterhub/pull/4214) ([@yuvipanda](https://github.com/yuvipanda), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics), [@minrk](https://github.com/minrk))
- Allow named_server_limit_per_user type to be callable [#4053](https://github.com/jupyterhub/jupyterhub/pull/4053) ([@danilopeixoto](https://github.com/danilopeixoto), [@minrk](https://github.com/minrk), [@GeorgianaElena](https://github.com/GeorgianaElena), [@dietmarw](https://github.com/dietmarw))

#### Bugs fixed

- make current_user available to handle_logout hook [#4230](https://github.com/jupyterhub/jupyterhub/pull/4230) ([@minrk](https://github.com/minrk), [@yuvipanda](https://github.com/yuvipanda))
- Fully resolve requested scopes in oauth [#4063](https://github.com/jupyterhub/jupyterhub/pull/4063) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Fix crash when removing scopes attribute from an existing role [#4045](https://github.com/jupyterhub/jupyterhub/pull/4045) ([@miwig](https://github.com/miwig), [@minrk](https://github.com/minrk))
- Pass launch_instance args on correctly. [#4039](https://github.com/jupyterhub/jupyterhub/pull/4039) ([@hjoliver](https://github.com/hjoliver), [@minrk](https://github.com/minrk), [@timeu](https://github.com/timeu))
- Fix Dockerfile yarn JSX build [#4034](https://github.com/jupyterhub/jupyterhub/pull/4034) ([@manics](https://github.com/manics), [@consideRatio](https://github.com/consideRatio), [@utkarshgupta137](https://github.com/utkarshgupta137))

#### Maintenance and upkeep improvements

- ci: update database image versions [#4233](https://github.com/jupyterhub/jupyterhub/pull/4233) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- selenium: update next_url after waiting for it to change [#4225](https://github.com/jupyterhub/jupyterhub/pull/4225) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- maint: add test to extras_require, remove greenlet workaround, test final py311, misc cleanup [#4223](https://github.com/jupyterhub/jupyterhub/pull/4223) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- pre-commit: add autoflake and make flake8 checks stricter [#4219](https://github.com/jupyterhub/jupyterhub/pull/4219) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- flake8: cleanup unused/redundant config [#4216](https://github.com/jupyterhub/jupyterhub/pull/4216) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk))
- ci: use non-deprecated codecov uploader [#4187](https://github.com/jupyterhub/jupyterhub/pull/4187) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk))
- jsx: remove unused useState [#4173](https://github.com/jupyterhub/jupyterhub/pull/4173) ([@liliyao2022](https://github.com/liliyao2022), [@minrk](https://github.com/minrk))
- Deleted unused failRegexEvent [#4172](https://github.com/jupyterhub/jupyterhub/pull/4172) ([@liliyao2022](https://github.com/liliyao2022), [@minrk](https://github.com/minrk))
- set stacklevel for oauth_scopes deprecation warning [#4064](https://github.com/jupyterhub/jupyterhub/pull/4064) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- setup.py: require npm, check that NPM CSS JSX commands succeed [#4035](https://github.com/jupyterhub/jupyterhub/pull/4035) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk))
- Add browser-based tests with Selenium [#4026](https://github.com/jupyterhub/jupyterhub/pull/4026) ([@mouse1203](https://github.com/mouse1203), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Documentation improvements

- clarify docstrings for default_server_name [#4240](https://github.com/jupyterhub/jupyterhub/pull/4240) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics), [@behrmann](https://github.com/behrmann))
- changelog for 1.5.1 [#4234](https://github.com/jupyterhub/jupyterhub/pull/4234) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@mriedem](https://github.com/mriedem))
- docs: refresh conf.py, add opengraph and rediraffe extensions [#4227](https://github.com/jupyterhub/jupyterhub/pull/4227) ([@consideRatio](https://github.com/consideRatio), [@choldgraf](https://github.com/choldgraf), [@minrk](https://github.com/minrk))
- docs: sphinx config cleanup, removing epub build, fix build warnings [#4222](https://github.com/jupyterhub/jupyterhub/pull/4222) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk), [@choldgraf](https://github.com/choldgraf))
- grammar in security-basics.rst [#4210](https://github.com/jupyterhub/jupyterhub/pull/4210) ([@ArafatAbdussalam](https://github.com/ArafatAbdussalam), [@minrk](https://github.com/minrk))
- avoid contraction in setup.rst [#4209](https://github.com/jupyterhub/jupyterhub/pull/4209) ([@ArafatAbdussalam](https://github.com/ArafatAbdussalam), [@minrk](https://github.com/minrk))
- improved the grammatical structure [#4208](https://github.com/jupyterhub/jupyterhub/pull/4208) ([@ArafatAbdussalam](https://github.com/ArafatAbdussalam), [@yuvipanda](https://github.com/yuvipanda))
- [docs] typo in access:servers scope [#4204](https://github.com/jupyterhub/jupyterhub/pull/4204) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- highlight "what is our actual goal" in faq [#4186](https://github.com/jupyterhub/jupyterhub/pull/4186) ([@emmanuella194](https://github.com/emmanuella194), [@minrk](https://github.com/minrk))
- Edits to institutional FAQ [#4185](https://github.com/jupyterhub/jupyterhub/pull/4185) ([@lumenCodes](https://github.com/lumenCodes), [@minrk](https://github.com/minrk))
- typos in example readme [#4171](https://github.com/jupyterhub/jupyterhub/pull/4171) ([@liliyao2022](https://github.com/liliyao2022), [@minrk](https://github.com/minrk))
- Updated deployment gallery links [#4170](https://github.com/jupyterhub/jupyterhub/pull/4170) ([@KaluBuikem](https://github.com/KaluBuikem), [@minrk](https://github.com/minrk))
- typo in contributing doc [#4169](https://github.com/jupyterhub/jupyterhub/pull/4169) ([@emmanuella194](https://github.com/emmanuella194), [@minrk](https://github.com/minrk))
- clarify CHP downsides in proxy doc [#4168](https://github.com/jupyterhub/jupyterhub/pull/4168) ([@lumenCodes](https://github.com/lumenCodes), [@minrk](https://github.com/minrk))
- Proofread services.md [#4167](https://github.com/jupyterhub/jupyterhub/pull/4167) ([@lumenCodes](https://github.com/lumenCodes), [@minrk](https://github.com/minrk))
- Welcome first-time contributors to the forum [#4166](https://github.com/jupyterhub/jupyterhub/pull/4166) ([@lumenCodes](https://github.com/lumenCodes), [@minrk](https://github.com/minrk))
- Typo in institutional-faq [#4162](https://github.com/jupyterhub/jupyterhub/pull/4162) ([@liliyao2022](https://github.com/liliyao2022), [@minrk](https://github.com/minrk))
- Improve text in proxy docs [#4161](https://github.com/jupyterhub/jupyterhub/pull/4161) ([@Christiandike](https://github.com/Christiandike), [@minrk](https://github.com/minrk))
- revise sudo config documentation [#4160](https://github.com/jupyterhub/jupyterhub/pull/4160) ([@Christiandike](https://github.com/Christiandike), [@minrk](https://github.com/minrk))
- Typo in roadmap.md [#4159](https://github.com/jupyterhub/jupyterhub/pull/4159) ([@liliyao2022](https://github.com/liliyao2022), [@minrk](https://github.com/minrk))
- fixes in jsx/README.md [#4158](https://github.com/jupyterhub/jupyterhub/pull/4158) ([@liliyao2022](https://github.com/liliyao2022), [@minrk](https://github.com/minrk))
- Improve JupyterHub's REST API doc [#4157](https://github.com/jupyterhub/jupyterhub/pull/4157) ([@Uzor13](https://github.com/Uzor13), [@minrk](https://github.com/minrk))
- Update dockerfile README [#4156](https://github.com/jupyterhub/jupyterhub/pull/4156) ([@liliyao2022](https://github.com/liliyao2022), [@minrk](https://github.com/minrk))
- Add link to OAuth 2 [#4155](https://github.com/jupyterhub/jupyterhub/pull/4155) ([@Christiandike](https://github.com/Christiandike), [@minrk](https://github.com/minrk))
- Remove redundant ref target for roles [#4154](https://github.com/jupyterhub/jupyterhub/pull/4154) ([@minrk](https://github.com/minrk))
- Consistent capitalization of Authenticator [#4153](https://github.com/jupyterhub/jupyterhub/pull/4153) ([@Teniola-theDev](https://github.com/Teniola-theDev), [@minrk](https://github.com/minrk))
- Link back to rbac from use-cases [#4152](https://github.com/jupyterhub/jupyterhub/pull/4152) ([@emmanuella194](https://github.com/emmanuella194), [@minrk](https://github.com/minrk))
- grammar improvements in quickstart.md [#4150](https://github.com/jupyterhub/jupyterhub/pull/4150) ([@liliyao2022](https://github.com/liliyao2022), [@minrk](https://github.com/minrk))
- update/spawners.md [#4148](https://github.com/jupyterhub/jupyterhub/pull/4148) ([@Christiandike](https://github.com/Christiandike), [@sgibson91](https://github.com/sgibson91))
- oauth doc: added punctuations and capitalized words where necessary [#4147](https://github.com/jupyterhub/jupyterhub/pull/4147) ([@Teebarh](https://github.com/Teebarh), [@minrk](https://github.com/minrk))
- Update to the spawner basic file [#4146](https://github.com/jupyterhub/jupyterhub/pull/4146) ([@lumenCodes](https://github.com/lumenCodes), [@minrk](https://github.com/minrk))
- Added text to documentation for more readability [#4145](https://github.com/jupyterhub/jupyterhub/pull/4145) ([@softkeldozy](https://github.com/softkeldozy), [@minrk](https://github.com/minrk))
- add link to rbac index from implementation [#4140](https://github.com/jupyterhub/jupyterhub/pull/4140) ([@Joel-Ando](https://github.com/Joel-Ando), [@minrk](https://github.com/minrk))
- highlight note about the docker image scope [#4139](https://github.com/jupyterhub/jupyterhub/pull/4139) ([@Joel-Ando](https://github.com/Joel-Ando), [@minrk](https://github.com/minrk))
- Update wording in web security docs [#4136](https://github.com/jupyterhub/jupyterhub/pull/4136) ([@yamakat](https://github.com/yamakat), [@minrk](https://github.com/minrk))
- update websecurity.md [#4135](https://github.com/jupyterhub/jupyterhub/pull/4135) ([@Christiandike](https://github.com/Christiandike), [@sgibson91](https://github.com/sgibson91), [@minrk](https://github.com/minrk))
- I capitalized cli and added y to jupterhub [#4133](https://github.com/jupyterhub/jupyterhub/pull/4133) ([@Teniola-theDev](https://github.com/Teniola-theDev), [@sgibson91](https://github.com/sgibson91))
- update spawners-basics.md [#4132](https://github.com/jupyterhub/jupyterhub/pull/4132) ([@ToobaJamal](https://github.com/ToobaJamal), [@minrk](https://github.com/minrk))
- refine text in template docs. [#4130](https://github.com/jupyterhub/jupyterhub/pull/4130) ([@lumenCodes](https://github.com/lumenCodes), [@minrk](https://github.com/minrk))
- reorder REST API doc [#4129](https://github.com/jupyterhub/jupyterhub/pull/4129) ([@lumenCodes](https://github.com/lumenCodes), [@minrk](https://github.com/minrk))
- update troubleshooting.md docs [#4127](https://github.com/jupyterhub/jupyterhub/pull/4127) ([@ArafatAbdussalam](https://github.com/ArafatAbdussalam), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Improve clarity in troubleshooting doc [#4126](https://github.com/jupyterhub/jupyterhub/pull/4126) ([@PoorvajaRayas](https://github.com/PoorvajaRayas), [@minrk](https://github.com/minrk))
- Add concrete steps to services-basics [#4124](https://github.com/jupyterhub/jupyterhub/pull/4124) ([@AdrianaHelga](https://github.com/AdrianaHelga), [@minrk](https://github.com/minrk))
- Formatting changes to tests.rst [#4119](https://github.com/jupyterhub/jupyterhub/pull/4119) ([@PoorvajaRayas](https://github.com/PoorvajaRayas), [@minrk](https://github.com/minrk))
- Capitalization typo in troubleshooting.md [#4118](https://github.com/jupyterhub/jupyterhub/pull/4118) ([@falyne](https://github.com/falyne), [@minrk](https://github.com/minrk))
- Fix duplicate statement in upgrading doc [#4116](https://github.com/jupyterhub/jupyterhub/pull/4116) ([@Eshy10](https://github.com/Eshy10), [@minrk](https://github.com/minrk))
- Issue #41 - Documentation reviewed, made concise and beginners friendly, added a JupyterHub image [#4114](https://github.com/jupyterhub/jupyterhub/pull/4114) ([@alexanderchosen](https://github.com/alexanderchosen), [@sgibson91](https://github.com/sgibson91))
- proofread upgrading docs [#4113](https://github.com/jupyterhub/jupyterhub/pull/4113) ([@EstherChristopher](https://github.com/EstherChristopher), [@minrk](https://github.com/minrk))
- Typo in templates.md [#4111](https://github.com/jupyterhub/jupyterhub/pull/4111) ([@zeelyha](https://github.com/zeelyha), [@minrk](https://github.com/minrk))
- Reviewed the documentation [#4109](https://github.com/jupyterhub/jupyterhub/pull/4109) ([@EstherChristopher](https://github.com/EstherChristopher), [@minrk](https://github.com/minrk))
- Edited and restructured `server-api` file [#4106](https://github.com/jupyterhub/jupyterhub/pull/4106) ([@alwasega](https://github.com/alwasega), [@minrk](https://github.com/minrk))
- Proofread and Improve security-basics.rst [#4098](https://github.com/jupyterhub/jupyterhub/pull/4098) ([@NPDebs](https://github.com/NPDebs), [@minrk](https://github.com/minrk))
- Modifications to URLs docs [#4097](https://github.com/jupyterhub/jupyterhub/pull/4097) ([@Mackenzie-OO7](https://github.com/Mackenzie-OO7), [@minrk](https://github.com/minrk))
- Link reference to github oauth config with jupyter [#4096](https://github.com/jupyterhub/jupyterhub/pull/4096) ([@Christiandike](https://github.com/Christiandike), [@GeorgianaElena](https://github.com/GeorgianaElena))
- Update config-proxy.md [#4095](https://github.com/jupyterhub/jupyterhub/pull/4095) ([@Goodiec](https://github.com/Goodiec), [@minrk](https://github.com/minrk), [@ryanlovett](https://github.com/ryanlovett))
- Fixed typos and added punctuations [#4094](https://github.com/jupyterhub/jupyterhub/pull/4094) ([@Busayo-ojo](https://github.com/Busayo-ojo), [@minrk](https://github.com/minrk), [@GeorgianaElena](https://github.com/GeorgianaElena))
- Fix typo [#4093](https://github.com/jupyterhub/jupyterhub/pull/4093) ([@Achele](https://github.com/Achele), [@GeorgianaElena](https://github.com/GeorgianaElena))
- modified announcement README and config.py [#4092](https://github.com/jupyterhub/jupyterhub/pull/4092) ([@Temidayo32](https://github.com/Temidayo32), [@sgibson91](https://github.com/sgibson91))
- Update config-user-env.md [#4091](https://github.com/jupyterhub/jupyterhub/pull/4091) ([@Goodiec](https://github.com/Goodiec), [@minrk](https://github.com/minrk), [@GeorgianaElena](https://github.com/GeorgianaElena))
- Restructured Community communication channels file [#4090](https://github.com/jupyterhub/jupyterhub/pull/4090) ([@alwasega](https://github.com/alwasega), [@minrk](https://github.com/minrk))
- Update tech-implementation.md [#4089](https://github.com/jupyterhub/jupyterhub/pull/4089) ([@Christiandike](https://github.com/Christiandike), [@GeorgianaElena](https://github.com/GeorgianaElena), [@minrk](https://github.com/minrk), [@KaluBuikem](https://github.com/KaluBuikem), [@Ginohmk](https://github.com/Ginohmk))
- Grammatical/link fixes in upgrading doc [#4088](https://github.com/jupyterhub/jupyterhub/pull/4088) ([@ToobaJamal](https://github.com/ToobaJamal), [@minrk](https://github.com/minrk), [@Mackenzie-OO7](https://github.com/Mackenzie-OO7))
- Updated log message docs [#4086](https://github.com/jupyterhub/jupyterhub/pull/4086) ([@ArafatAbdussalam](https://github.com/ArafatAbdussalam), [@minrk](https://github.com/minrk))
- Update troubleshooting.md [#4085](https://github.com/jupyterhub/jupyterhub/pull/4085) ([@Goodiec](https://github.com/Goodiec), [@minrk](https://github.com/minrk), [@GeorgianaElena](https://github.com/GeorgianaElena))
- Refine text in documentation index [#4084](https://github.com/jupyterhub/jupyterhub/pull/4084) ([@melissakirabo](https://github.com/melissakirabo), [@minrk](https://github.com/minrk))
- updated websecurity.md [#4083](https://github.com/jupyterhub/jupyterhub/pull/4083) ([@ArafatAbdussalam](https://github.com/ArafatAbdussalam), [@minrk](https://github.com/minrk))
- Migrate community channels to markdown, update text [#4081](https://github.com/jupyterhub/jupyterhub/pull/4081) ([@Christiandike](https://github.com/Christiandike), [@GeorgianaElena](https://github.com/GeorgianaElena), [@minrk](https://github.com/minrk))
- Improve the documentation about log messages [#4079](https://github.com/jupyterhub/jupyterhub/pull/4079) ([@mahamtariq58](https://github.com/mahamtariq58), [@GeorgianaElena](https://github.com/GeorgianaElena))
- Update index.rst [#4074](https://github.com/jupyterhub/jupyterhub/pull/4074) ([@ToobaJamal](https://github.com/ToobaJamal), [@minrk](https://github.com/minrk), [@GeorgianaElena](https://github.com/GeorgianaElena))
- improved the quickstart docker guide [#4073](https://github.com/jupyterhub/jupyterhub/pull/4073) ([@ikeadeoyin](https://github.com/ikeadeoyin), [@minrk](https://github.com/minrk))
- [doc] templates: updated obsolete links and made wordings clearer [#4072](https://github.com/jupyterhub/jupyterhub/pull/4072) ([@ruqayaahh](https://github.com/ruqayaahh), [@minrk](https://github.com/minrk))
- Improve rbac/roles documentation [#4071](https://github.com/jupyterhub/jupyterhub/pull/4071) ([@NPDebs](https://github.com/NPDebs), [@minrk](https://github.com/minrk))
- Modifications to Technical Overview Docs [#4070](https://github.com/jupyterhub/jupyterhub/pull/4070) ([@Mackenzie-OO7](https://github.com/Mackenzie-OO7), [@GeorgianaElena](https://github.com/GeorgianaElena), [@minrk](https://github.com/minrk))
- Modifications is testing docs [#4069](https://github.com/jupyterhub/jupyterhub/pull/4069) ([@chicken-biryani](https://github.com/chicken-biryani), [@GeorgianaElena](https://github.com/GeorgianaElena), [@manics](https://github.com/manics), [@minrk](https://github.com/minrk))
- Update setup.rst [#4068](https://github.com/jupyterhub/jupyterhub/pull/4068) ([@Goodiec](https://github.com/Goodiec), [@GeorgianaElena](https://github.com/GeorgianaElena), [@minrk](https://github.com/minrk))
- fixed some typos and also added links #41 [#4067](https://github.com/jupyterhub/jupyterhub/pull/4067) ([@Uzor13](https://github.com/Uzor13), [@GeorgianaElena](https://github.com/GeorgianaElena), [@manics](https://github.com/manics), [@chicken-biryani](https://github.com/chicken-biryani))
- Modification in community channels docs [#4065](https://github.com/jupyterhub/jupyterhub/pull/4065) ([@chicken-biryani](https://github.com/chicken-biryani), [@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- Add note about building the docs from Windows [#4061](https://github.com/jupyterhub/jupyterhub/pull/4061) ([@Temidayo32](https://github.com/Temidayo32), [@consideRatio](https://github.com/consideRatio))
- mention c.Spawner.auth_state_hook in Authenticator auth state docs [#4046](https://github.com/jupyterhub/jupyterhub/pull/4046) ([@Neeraj-Natu](https://github.com/Neeraj-Natu), [@minrk](https://github.com/minrk))
- Add draft capacity planning doc [#4008](https://github.com/jupyterhub/jupyterhub/pull/4008) ([@minrk](https://github.com/minrk), [@choldgraf](https://github.com/choldgraf))
- Some suggestions from reading through the docs [#2641](https://github.com/jupyterhub/jupyterhub/pull/2641) ([@ericdill](https://github.com/ericdill), [@minrk](https://github.com/minrk), [@manics](https://github.com/manics), [@willingc](https://github.com/willingc))

#### API and Breaking Changes

- deprecate JupyterHub.extra_handlers [#4236](https://github.com/jupyterhub/jupyterhub/pull/4236) ([@minrk](https://github.com/minrk), [@GeorgianaElena](https://github.com/GeorgianaElena))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2022-09-09&to=2022-12-05&type=c))

[@Achele](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AAchele+updated%3A2022-09-09..2022-12-05&type=Issues) | [@AdrianaHelga](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AAdrianaHelga+updated%3A2022-09-09..2022-12-05&type=Issues) | [@alexanderchosen](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aalexanderchosen+updated%3A2022-09-09..2022-12-05&type=Issues) | [@alwasega](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aalwasega+updated%3A2022-09-09..2022-12-05&type=Issues) | [@ArafatAbdussalam](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AArafatAbdussalam+updated%3A2022-09-09..2022-12-05&type=Issues) | [@behrmann](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abehrmann+updated%3A2022-09-09..2022-12-05&type=Issues) | [@bl-aire](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abl-aire+updated%3A2022-09-09..2022-12-05&type=Issues) | [@Busayo-ojo](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ABusayo-ojo+updated%3A2022-09-09..2022-12-05&type=Issues) | [@chicken-biryani](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Achicken-biryani+updated%3A2022-09-09..2022-12-05&type=Issues) | [@choldgraf](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acholdgraf+updated%3A2022-09-09..2022-12-05&type=Issues) | [@Christiandike](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AChristiandike+updated%3A2022-09-09..2022-12-05&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2022-09-09..2022-12-05&type=Issues) | [@danilopeixoto](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adanilopeixoto+updated%3A2022-09-09..2022-12-05&type=Issues) | [@dependabot](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adependabot+updated%3A2022-09-09..2022-12-05&type=Issues) | [@dietmarw](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adietmarw+updated%3A2022-09-09..2022-12-05&type=Issues) | [@Emenyi95](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AEmenyi95+updated%3A2022-09-09..2022-12-05&type=Issues) | [@emmanuella194](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aemmanuella194+updated%3A2022-09-09..2022-12-05&type=Issues) | [@ericdill](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aericdill+updated%3A2022-09-09..2022-12-05&type=Issues) | [@Eshy10](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AEshy10+updated%3A2022-09-09..2022-12-05&type=Issues) | [@EstherChristopher](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AEstherChristopher+updated%3A2022-09-09..2022-12-05&type=Issues) | [@falyne](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Afalyne+updated%3A2022-09-09..2022-12-05&type=Issues) | [@GeorgianaElena](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AGeorgianaElena+updated%3A2022-09-09..2022-12-05&type=Issues) | [@Ginohmk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AGinohmk+updated%3A2022-09-09..2022-12-05&type=Issues) | [@github-actions](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Agithub-actions+updated%3A2022-09-09..2022-12-05&type=Issues) | [@Goodiec](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AGoodiec+updated%3A2022-09-09..2022-12-05&type=Issues) | [@hjoliver](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ahjoliver+updated%3A2022-09-09..2022-12-05&type=Issues) | [@hsadia538](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ahsadia538+updated%3A2022-09-09..2022-12-05&type=Issues) | [@ikeadeoyin](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aikeadeoyin+updated%3A2022-09-09..2022-12-05&type=Issues) | [@iLynette](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AiLynette+updated%3A2022-09-09..2022-12-05&type=Issues) | [@Joel-Ando](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AJoel-Ando+updated%3A2022-09-09..2022-12-05&type=Issues) | [@KaluBuikem](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AKaluBuikem+updated%3A2022-09-09..2022-12-05&type=Issues) | [@kamzzy](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akamzzy+updated%3A2022-09-09..2022-12-05&type=Issues) | [@liliyao2022](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aliliyao2022+updated%3A2022-09-09..2022-12-05&type=Issues) | [@lumenCodes](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AlumenCodes+updated%3A2022-09-09..2022-12-05&type=Issues) | [@Mackenzie-OO7](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AMackenzie-OO7+updated%3A2022-09-09..2022-12-05&type=Issues) | [@mahamtariq58](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amahamtariq58+updated%3A2022-09-09..2022-12-05&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2022-09-09..2022-12-05&type=Issues) | [@melissakirabo](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amelissakirabo+updated%3A2022-09-09..2022-12-05&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2022-09-09..2022-12-05&type=Issues) | [@miwig](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amiwig+updated%3A2022-09-09..2022-12-05&type=Issues) | [@mouse1203](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amouse1203+updated%3A2022-09-09..2022-12-05&type=Issues) | [@mriedem](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amriedem+updated%3A2022-09-09..2022-12-05&type=Issues) | [@Neeraj-Natu](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ANeeraj-Natu+updated%3A2022-09-09..2022-12-05&type=Issues) | [@NPDebs](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ANPDebs+updated%3A2022-09-09..2022-12-05&type=Issues) | [@PoorvajaRayas](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3APoorvajaRayas+updated%3A2022-09-09..2022-12-05&type=Issues) | [@pre-commit-ci](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apre-commit-ci+updated%3A2022-09-09..2022-12-05&type=Issues) | [@ruqayaahh](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aruqayaahh+updated%3A2022-09-09..2022-12-05&type=Issues) | [@ryanlovett](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aryanlovett+updated%3A2022-09-09..2022-12-05&type=Issues) | [@sgibson91](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asgibson91+updated%3A2022-09-09..2022-12-05&type=Issues) | [@softkeldozy](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asoftkeldozy+updated%3A2022-09-09..2022-12-05&type=Issues) | [@Teebarh](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ATeebarh+updated%3A2022-09-09..2022-12-05&type=Issues) | [@Temidayo32](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ATemidayo32+updated%3A2022-09-09..2022-12-05&type=Issues) | [@Teniola-theDev](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ATeniola-theDev+updated%3A2022-09-09..2022-12-05&type=Issues) | [@timeu](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atimeu+updated%3A2022-09-09..2022-12-05&type=Issues) | [@ToobaJamal](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AToobaJamal+updated%3A2022-09-09..2022-12-05&type=Issues) | [@utkarshgupta137](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Autkarshgupta137+updated%3A2022-09-09..2022-12-05&type=Issues) | [@Uzor13](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AUzor13+updated%3A2022-09-09..2022-12-05&type=Issues) | [@willingc](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awillingc+updated%3A2022-09-09..2022-12-05&type=Issues) | [@yamakat](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayamakat+updated%3A2022-09-09..2022-12-05&type=Issues) | [@yuvipanda](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2022-09-09..2022-12-05&type=Issues) | [@zeelyha](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Azeelyha+updated%3A2022-09-09..2022-12-05&type=Issues)

## 3.0

### 3.0.0 - 2022-09-08

3.0 is a major upgrade, but a small one.

It qualifies as a major upgrade because of two changes:

1. It includes a database schema change (`jupyterhub --upgrade-db`).
   The schema change should not be disruptive, but we've decided that
   any schema change qualifies as a major version upgrade.
2. We've dropped support for Python 3.6, which reached End-of-Life in 2021.
   If you are using at least Python 3.7, this change should have no effect.

The database schema change is small and should not be disruptive,
but downgrading is always harder than upgrading after a db migration,
which makes rolling back the update more likely to be problematic.

#### Changes in RBAC

The biggest changes in 3.0 relate to {ref}`RBAC`,
which also means they shouldn't affect most users.
The users most affected will be JupyterHub admins using JupyterHub roles
extensively to define user permissions.

After testing 2.0 in the wild,
we learned that we had used _roles_ in a few places that should have been _scopes_.
Specifically, OAuth tokens now have _scopes_ instead of _roles_
(and token-issuing oauth clients now have `allowed_scopes` instead of `allowed_roles`).
The consequences should be fairly transparent to users,
but anyone who ran into the restrictions of roles in the oauth process
should find scopes easier to work with.
We tried not to break anything here, so any prior use of roles will still work with a deprecation,
but the role will be resolved _immediately_ at token-issue time,
rather than every time the token is used.

This especially came up testing the new {ref}`custom-scopes` feature.
Authors of JupyterHub-authenticated services can now extend JupyterHub's RBAC functionality to define their own scopes,
and assign them to users and groups via roles.
This can be used to e.g. limit student/grader/instructor permissions in a grading service,
or grant instructors read-only access to their students' single-user servers starting with upcoming Jupyter Server 2.0.

Further extending granular control of permissions,
we have added `!service` and `!server` filters for scopes ({ref}`self-referencing-filters`),
like we had for `!user`.

Access to the admin UI is now governed by a dedicated `admin-ui` scope,
rather than combined `admin:servers` and `admin:users` in 2.0.
More info in {ref}`available-scopes-target`.

#### More highlights

- The admin UI can now show more detailed info about users and their servers in a drop-down details table:

  ![Details view in admin UI](/images/dropdown-details-3.0.png)

- Several bugfixes and improvements in the new admin UI.
- Direct access to the Hub's database is deprecated.
  We intend to change the database connection lifecycle in the future to enable scalability and high-availability (HA),
  and limiting where connections and transactions can occur is an important part of making that possible.
- Lots more bugfixes and error-handling improvements.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/2.3.1...3.0.0))

#### New features added

- Add ConfigurableHTTPProxy.log_level [#3962](https://github.com/jupyterhub/jupyterhub/pull/3962) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk))
- include stopped servers in user model [#3909](https://github.com/jupyterhub/jupyterhub/pull/3909) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- allow HubAuth to be async [#3883](https://github.com/jupyterhub/jupyterhub/pull/3883) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@sgibson91](https://github.com/sgibson91))
- add 'admin-ui' scope for access to the admin ui [#3878](https://github.com/jupyterhub/jupyterhub/pull/3878) ([@minrk](https://github.com/minrk), [@GeorgianaElena](https://github.com/GeorgianaElena), [@manics](https://github.com/manics))
- store scopes on oauth clients, too [#3877](https://github.com/jupyterhub/jupyterhub/pull/3877) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- !service and !server filters [#3851](https://github.com/jupyterhub/jupyterhub/pull/3851) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- allow user-defined custom scopes [#3713](https://github.com/jupyterhub/jupyterhub/pull/3713) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))

#### Enhancements made

- Integrate Pagination API into Admin JSX [#4002](https://github.com/jupyterhub/jupyterhub/pull/4002) ([@naatebarber](https://github.com/naatebarber), [@minrk](https://github.com/minrk))
- admin: format user/server-info tables [#4001](https://github.com/jupyterhub/jupyterhub/pull/4001) ([@minrk](https://github.com/minrk))
- add correct autocomplete fields for login form [#3958](https://github.com/jupyterhub/jupyterhub/pull/3958) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- memoize some scope functions [#3850](https://github.com/jupyterhub/jupyterhub/pull/3850) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- Tokens have scopes instead of roles [#3833](https://github.com/jupyterhub/jupyterhub/pull/3833) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Bugs fixed

- Use correct expiration labels in drop-down menu on token page. [#4022](https://github.com/jupyterhub/jupyterhub/pull/4022) ([@possiblyMikeB](https://github.com/possiblyMikeB), [@consideRatio](https://github.com/consideRatio))
- avoid database error on repeated group name in sync_groups [#4019](https://github.com/jupyterhub/jupyterhub/pull/4019) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- reset offset to 0 on name filter change [#4018](https://github.com/jupyterhub/jupyterhub/pull/4018) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- admin: avoid redundant client-side username validation in edit-user [#4016](https://github.com/jupyterhub/jupyterhub/pull/4016) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- restore trimming of username input [#4011](https://github.com/jupyterhub/jupyterhub/pull/4011) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- nbclassic extension name has been renamed [#3971](https://github.com/jupyterhub/jupyterhub/pull/3971) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Fix disabling of individual page template announcements [#3969](https://github.com/jupyterhub/jupyterhub/pull/3969) ([@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics), [@minrk](https://github.com/minrk))
- validate proxy.extra_routes [#3967](https://github.com/jupyterhub/jupyterhub/pull/3967) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Fix GET /api/proxy with pagination [#3960](https://github.com/jupyterhub/jupyterhub/pull/3960) ([@cqzlxl](https://github.com/cqzlxl), [@minrk](https://github.com/minrk))
- FreeBSD, missing -n for pw useradd [#3953](https://github.com/jupyterhub/jupyterhub/pull/3953) ([@silenius](https://github.com/silenius), [@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- admin: Hub is responsible for username validation [#3936](https://github.com/jupyterhub/jupyterhub/pull/3936) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@NarekA](https://github.com/NarekA), [@yuvipanda](https://github.com/yuvipanda))
- admin: Fix spawn page link for default server [#3935](https://github.com/jupyterhub/jupyterhub/pull/3935) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@benz0li](https://github.com/benz0li))
- let errors raised in an auth_state_hook halt spawn [#3908](https://github.com/jupyterhub/jupyterhub/pull/3908) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Escape named server name [#3904](https://github.com/jupyterhub/jupyterhub/pull/3904) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk))

#### Maintenance and upkeep improvements

- Test 3.11 [#4013](https://github.com/jupyterhub/jupyterhub/pull/4013) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- [admin] update, clean jsx deps [#4000](https://github.com/jupyterhub/jupyterhub/pull/4000) ([@minrk](https://github.com/minrk))
- Avoid IOLoop.current in singleuser mixins [#3992](https://github.com/jupyterhub/jupyterhub/pull/3992) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Increase stacklevel for decorated warnings [#3978](https://github.com/jupyterhub/jupyterhub/pull/3978) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Bump Dockerfile base image to 22.04 [#3975](https://github.com/jupyterhub/jupyterhub/pull/3975) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- Avoid deprecated 'IOLoop.current' method [#3974](https://github.com/jupyterhub/jupyterhub/pull/3974) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- switch to importlib_metadata for entrypoints [#3937](https://github.com/jupyterhub/jupyterhub/pull/3937) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- pages.py: Remove unreachable code [#3921](https://github.com/jupyterhub/jupyterhub/pull/3921) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Build admin app in setup.py [#3914](https://github.com/jupyterhub/jupyterhub/pull/3914) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk))
- Use isort for import formatting [#3852](https://github.com/jupyterhub/jupyterhub/pull/3852) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@choldgraf](https://github.com/choldgraf), [@yuvipanda](https://github.com/yuvipanda))

#### Documentation improvements

- document oauth_no_confirm in services [#4012](https://github.com/jupyterhub/jupyterhub/pull/4012) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Remove outdated cookie-secret note in security docs [#3997](https://github.com/jupyterhub/jupyterhub/pull/3997) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Update Contributing documentation [#3915](https://github.com/jupyterhub/jupyterhub/pull/3915) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk))
- `jupyter troubleshooting` ➡️ `jupyter troubleshoot` [#3903](https://github.com/jupyterhub/jupyterhub/pull/3903) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- `admin_access` no longer works as it is overridden by RBAC scopes [#3899](https://github.com/jupyterhub/jupyterhub/pull/3899) ([@manics](https://github.com/manics), [@minrk](https://github.com/minrk))
- Document the 'display' attribute of services [#3895](https://github.com/jupyterhub/jupyterhub/pull/3895) ([@yuvipanda](https://github.com/yuvipanda), [@minrk](https://github.com/minrk), [@sgibson91](https://github.com/sgibson91))
- remove apache NE flag as it prevents opening folders and renaming fil… [#3891](https://github.com/jupyterhub/jupyterhub/pull/3891) ([@bbrauns](https://github.com/bbrauns), [@minrk](https://github.com/minrk))

#### API and Breaking Changes

- Require Python 3.7 [#3976](https://github.com/jupyterhub/jupyterhub/pull/3976) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- Deprecate Authenticator.db, Spawner.db [#3885](https://github.com/jupyterhub/jupyterhub/pull/3885) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2022-03-14&to=2022-09-07&type=c))

[@ajcollett](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aajcollett+updated%3A2022-08-02..2022-09-07&type=Issues) | [@bbrauns](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abbrauns+updated%3A2022-03-14..2022-08-02&type=Issues) | [@benz0li](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abenz0li+updated%3A2022-03-14..2022-08-02&type=Issues) | [@betatim](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abetatim+updated%3A2022-03-14..2022-08-02&type=Issues) | [@blink1073](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ablink1073+updated%3A2022-03-14..2022-08-02&type=Issues) | [@brospars](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abrospars+updated%3A2022-03-14..2022-08-02&type=Issues) | [@Carreau](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ACarreau+updated%3A2022-03-14..2022-08-02&type=Issues) | [@choldgraf](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acholdgraf+updated%3A2022-03-14..2022-08-02&type=Issues) | [@cmd-ntrf](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acmd-ntrf+updated%3A2022-03-14..2022-08-02&type=Issues) | [@code-review-doctor](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acode-review-doctor+updated%3A2022-03-14..2022-08-02&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2022-03-14..2022-08-02&type=Issues) | [@cqzlxl](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acqzlxl+updated%3A2022-03-14..2022-08-02&type=Issues) | [@dependabot](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adependabot+updated%3A2022-03-14..2022-08-02&type=Issues) | [@fabianbaier](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Afabianbaier+updated%3A2022-03-14..2022-08-02&type=Issues) | [@GeorgianaElena](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AGeorgianaElena+updated%3A2022-03-14..2022-08-02&type=Issues) | [@github-actions](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Agithub-actions+updated%3A2022-03-14..2022-08-02&type=Issues) | [@hansen-m](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ahansen-m+updated%3A2022-03-14..2022-08-02&type=Issues) | [@huage1994](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ahuage1994+updated%3A2022-03-14..2022-08-02&type=Issues) | [@jbaksta](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajbaksta+updated%3A2022-03-14..2022-08-02&type=Issues) | [@jgwerner](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajgwerner+updated%3A2022-03-14..2022-08-02&type=Issues) | [@jhermann](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajhermann+updated%3A2022-03-14..2022-08-02&type=Issues) | [@johnkpark](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajohnkpark+updated%3A2022-03-14..2022-08-02&type=Issues) | [@jwclark](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajwclark+updated%3A2022-03-14..2022-08-02&type=Issues) | [@maluhoss](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amaluhoss+updated%3A2022-03-14..2022-08-02&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2022-03-14..2022-08-02&type=Issues) | [@mathematicalmichael](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amathematicalmichael+updated%3A2022-03-14..2022-08-02&type=Issues) | [@meeseeksdev](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ameeseeksdev+updated%3A2022-03-14..2022-08-02&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2022-03-14..2022-08-02&type=Issues) | [@mriedem](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amriedem+updated%3A2022-03-14..2022-08-02&type=Issues) | [@naatebarber](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Anaatebarber+updated%3A2022-03-14..2022-08-02&type=Issues) | [@NarekA](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ANarekA+updated%3A2022-03-14..2022-08-02&type=Issues) | [@naveensrinivasan](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Anaveensrinivasan+updated%3A2022-03-14..2022-08-02&type=Issues) | [@nicorikken](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Anicorikken+updated%3A2022-03-14..2022-08-02&type=Issues) | [@nsshah1288](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ansshah1288+updated%3A2022-03-14..2022-08-02&type=Issues) | [@panruipr](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apanruipr+updated%3A2022-03-14..2022-08-02&type=Issues) | [@paulkerry1](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apaulkerry1+updated%3A2022-03-14..2022-08-02&type=Issues) | [@possiblyMikeB](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ApossiblyMikeB+updated%3A2022-08-02..2022-09-07&type=Issues) | [@pre-commit-ci](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apre-commit-ci+updated%3A2022-03-14..2022-08-02&type=Issues) | [@rcthomas](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arcthomas+updated%3A2022-03-14..2022-08-02&type=Issues) | [@robnagler](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arobnagler+updated%3A2022-03-14..2022-08-02&type=Issues) | [@rpwagner](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arpwagner+updated%3A2022-03-14..2022-08-02&type=Issues) | [@ryogesh](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aryogesh+updated%3A2022-03-14..2022-08-02&type=Issues) | [@sgibson91](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asgibson91+updated%3A2022-03-14..2022-08-02&type=Issues) | [@silenius](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asilenius+updated%3A2022-03-14..2022-08-02&type=Issues) | [@SonakshiGrover](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ASonakshiGrover+updated%3A2022-03-14..2022-08-02&type=Issues) | [@superfive666](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asuperfive666+updated%3A2022-08-02..2022-09-07&type=Issues) | [@tharwan](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atharwan+updated%3A2022-03-14..2022-08-02&type=Issues) | [@vpavlin](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Avpavlin+updated%3A2022-03-14..2022-08-02&type=Issues) | [@willingc](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awillingc+updated%3A2022-03-14..2022-08-02&type=Issues) | [@ykazakov](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aykazakov+updated%3A2022-03-14..2022-08-02&type=Issues) | [@yuvipanda](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2022-03-14..2022-08-02&type=Issues) | [@zoltan-fedor](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Azoltan-fedor+updated%3A2022-03-14..2022-08-02&type=Issues)

## 2.3

### 2.3.1 - 2022-06-06

This release includes a selection of bugfixes.

#### Bugs fixed

- use equality to filter token prefixes [#3910](https://github.com/jupyterhub/jupyterhub/pull/3910) ([@minrk](https://github.com/minrk), [@yuvipanda](https://github.com/yuvipanda))
- ensure custom template is loaded with jupyter-server notebook extension [#3919](https://github.com/jupyterhub/jupyterhub/pull/3919) ([@minrk](https://github.com/minrk), [@yuvipanda](https://github.com/yuvipanda))
- set default_url via config [#3918](https://github.com/jupyterhub/jupyterhub/pull/3918) ([@minrk](https://github.com/minrk), [@yuvipanda](https://github.com/yuvipanda))
- Force add existing certificates [#3906](https://github.com/jupyterhub/jupyterhub/pull/3906) ([@fabianbaier](https://github.com/fabianbaier), [@minrk](https://github.com/minrk))
- admin: make user-info table selectable [#3889](https://github.com/jupyterhub/jupyterhub/pull/3889) ([@johnkpark](https://github.com/johnkpark), [@minrk](https://github.com/minrk), [@naatebarber](https://github.com/naatebarber), [@NarekA](https://github.com/NarekA))
- ensure \_import_error is set when JUPYTERHUB_SINGLEUSER_APP is unavailable [#3837](https://github.com/jupyterhub/jupyterhub/pull/3837) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2022-05-06&to=2022-06-06&type=c))

[@bbrauns](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abbrauns+updated%3A2022-05-06..2022-06-06&type=Issues) | [@betatim](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abetatim+updated%3A2022-05-06..2022-06-06&type=Issues) | [@blink1073](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ablink1073+updated%3A2022-05-06..2022-06-06&type=Issues) | [@brospars](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abrospars+updated%3A2022-05-06..2022-06-06&type=Issues) | [@Carreau](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ACarreau+updated%3A2022-05-06..2022-06-06&type=Issues) | [@choldgraf](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acholdgraf+updated%3A2022-05-06..2022-06-06&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2022-05-06..2022-06-06&type=Issues) | [@fabianbaier](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Afabianbaier+updated%3A2022-05-06..2022-06-06&type=Issues) | [@GeorgianaElena](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AGeorgianaElena+updated%3A2022-05-06..2022-06-06&type=Issues) | [@github-actions](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Agithub-actions+updated%3A2022-05-06..2022-06-06&type=Issues) | [@hansen-m](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ahansen-m+updated%3A2022-05-06..2022-06-06&type=Issues) | [@jbaksta](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajbaksta+updated%3A2022-05-06..2022-06-06&type=Issues) | [@jgwerner](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajgwerner+updated%3A2022-05-06..2022-06-06&type=Issues) | [@jhermann](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajhermann+updated%3A2022-05-06..2022-06-06&type=Issues) | [@johnkpark](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajohnkpark+updated%3A2022-05-06..2022-06-06&type=Issues) | [@maluhoss](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amaluhoss+updated%3A2022-05-06..2022-06-06&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2022-05-06..2022-06-06&type=Issues) | [@mathematicalmichael](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amathematicalmichael+updated%3A2022-05-06..2022-06-06&type=Issues) | [@meeseeksdev](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ameeseeksdev+updated%3A2022-05-06..2022-06-06&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2022-05-06..2022-06-06&type=Issues) | [@mriedem](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amriedem+updated%3A2022-05-06..2022-06-06&type=Issues) | [@naatebarber](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Anaatebarber+updated%3A2022-05-06..2022-06-06&type=Issues) | [@NarekA](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ANarekA+updated%3A2022-05-06..2022-06-06&type=Issues) | [@nicorikken](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Anicorikken+updated%3A2022-05-06..2022-06-06&type=Issues) | [@nsshah1288](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ansshah1288+updated%3A2022-05-06..2022-06-06&type=Issues) | [@panruipr](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apanruipr+updated%3A2022-05-06..2022-06-06&type=Issues) | [@paulkerry1](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apaulkerry1+updated%3A2022-05-06..2022-06-06&type=Issues) | [@rcthomas](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arcthomas+updated%3A2022-05-06..2022-06-06&type=Issues) | [@robnagler](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arobnagler+updated%3A2022-05-06..2022-06-06&type=Issues) | [@ryogesh](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aryogesh+updated%3A2022-05-06..2022-06-06&type=Issues) | [@sgibson91](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asgibson91+updated%3A2022-05-06..2022-06-06&type=Issues) | [@SonakshiGrover](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ASonakshiGrover+updated%3A2022-05-06..2022-06-06&type=Issues) | [@tharwan](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atharwan+updated%3A2022-05-06..2022-06-06&type=Issues) | [@vpavlin](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Avpavlin+updated%3A2022-05-06..2022-06-06&type=Issues) | [@welcome](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awelcome+updated%3A2022-05-06..2022-06-06&type=Issues) | [@willingc](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awillingc+updated%3A2022-05-06..2022-06-06&type=Issues) | [@yuvipanda](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2022-05-06..2022-06-06&type=Issues) | [@zoltan-fedor](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Azoltan-fedor+updated%3A2022-05-06..2022-06-06&type=Issues)

### 2.3.0 - 2022-05-06

#### Enhancements made

- Admin Dashboard - Collapsible Details View [#3834](https://github.com/jupyterhub/jupyterhub/pull/3834) ([@NarekA](https://github.com/NarekA), [@minrk](https://github.com/minrk), [@ykazakov](https://github.com/ykazakov), [@johnkpark](https://github.com/johnkpark))
- Admin Dashboard - Add search bar for user name [#3827](https://github.com/jupyterhub/jupyterhub/pull/3827) ([@NarekA](https://github.com/NarekA), [@minrk](https://github.com/minrk), [@ykazakov](https://github.com/ykazakov))

#### Bugs fixed

- Cleanup everything on API shutdown [#3886](https://github.com/jupyterhub/jupyterhub/pull/3886) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics))
- don't confuse :// in next_url query params for a redirect hostname [#3876](https://github.com/jupyterhub/jupyterhub/pull/3876) ([@minrk](https://github.com/minrk), [@GeorgianaElena](https://github.com/GeorgianaElena))
- Search bar disabled on admin dashboard [#3863](https://github.com/jupyterhub/jupyterhub/pull/3863) ([@NarekA](https://github.com/NarekA), [@minrk](https://github.com/minrk))
- Do not store Spawner.ip/port on spawner.server during get_env [#3859](https://github.com/jupyterhub/jupyterhub/pull/3859) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics), [@consideRatio](https://github.com/consideRatio))
- Fix xsrf_cookie_kwargs ValueError [#3853](https://github.com/jupyterhub/jupyterhub/pull/3853) ([@jwclark](https://github.com/jwclark), [@minrk](https://github.com/minrk))
- ensure \_import_error is set when JUPYTERHUB_SINGLEUSER_APP is unavailable [#3837](https://github.com/jupyterhub/jupyterhub/pull/3837) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Maintenance and upkeep improvements

- Use log.exception when logging exceptions [#3882](https://github.com/jupyterhub/jupyterhub/pull/3882) ([@yuvipanda](https://github.com/yuvipanda), [@minrk](https://github.com/minrk), [@sgibson91](https://github.com/sgibson91))
- Missing `f` prefix on f-strings fix [#3874](https://github.com/jupyterhub/jupyterhub/pull/3874) ([@code-review-doctor](https://github.com/code-review-doctor), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- adopt pytest-asyncio asyncio_mode='auto' [#3841](https://github.com/jupyterhub/jupyterhub/pull/3841) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@manics](https://github.com/manics))
- remove lingering reference to distutils [#3835](https://github.com/jupyterhub/jupyterhub/pull/3835) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Documentation improvements

- Fix typo in REST API link in README.md [#3862](https://github.com/jupyterhub/jupyterhub/pull/3862) ([@cmd-ntrf](https://github.com/cmd-ntrf), [@consideRatio](https://github.com/consideRatio))
- The word `used` is duplicated in upgrade.md [#3849](https://github.com/jupyterhub/jupyterhub/pull/3849) ([@huage1994](https://github.com/huage1994), [@consideRatio](https://github.com/consideRatio))
- Some typos in docs [#3843](https://github.com/jupyterhub/jupyterhub/pull/3843) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Document version mismatch log message [#3839](https://github.com/jupyterhub/jupyterhub/pull/3839) ([@yuvipanda](https://github.com/yuvipanda), [@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2022-03-14&to=2022-05-05&type=c))

[@choldgraf](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acholdgraf+updated%3A2022-03-14..2022-05-05&type=Issues) | [@cmd-ntrf](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acmd-ntrf+updated%3A2022-03-14..2022-05-05&type=Issues) | [@code-review-doctor](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acode-review-doctor+updated%3A2022-03-14..2022-05-05&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2022-03-14..2022-05-05&type=Issues) | [@dependabot](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adependabot+updated%3A2022-03-14..2022-05-05&type=Issues) | [@GeorgianaElena](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AGeorgianaElena+updated%3A2022-03-14..2022-05-05&type=Issues) | [@github-actions](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Agithub-actions+updated%3A2022-03-14..2022-05-05&type=Issues) | [@huage1994](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ahuage1994+updated%3A2022-03-14..2022-05-05&type=Issues) | [@johnkpark](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajohnkpark+updated%3A2022-03-14..2022-05-05&type=Issues) | [@jwclark](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajwclark+updated%3A2022-03-14..2022-05-05&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2022-03-14..2022-05-05&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2022-03-14..2022-05-05&type=Issues) | [@NarekA](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ANarekA+updated%3A2022-03-14..2022-05-05&type=Issues) | [@pre-commit-ci](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apre-commit-ci+updated%3A2022-03-14..2022-05-05&type=Issues) | [@sgibson91](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asgibson91+updated%3A2022-03-14..2022-05-05&type=Issues) | [@ykazakov](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aykazakov+updated%3A2022-03-14..2022-05-05&type=Issues) | [@yuvipanda](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2022-03-14..2022-05-05&type=Issues)

## 2.2

### 2.2.2 2022-03-14

2.2.2 fixes a small regressions in 2.2.1.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/2.2.1...6c5e5452bc734dfd5c5a9482e4980b988ddd304e))

#### Bugs fixed

- Fix failure to update admin-react.js by re-compiling from our source [#3825](https://github.com/jupyterhub/jupyterhub/pull/3825) ([@NarekA](https://github.com/NarekA), [@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk), [@manics](https://github.com/manics))

#### Continuous integration improvements

- ci: standalone jsx workflow and verify compiled asset matches source code [#3826](https://github.com/jupyterhub/jupyterhub/pull/3826) ([@consideRatio](https://github.com/consideRatio), [@NarekA](https://github.com/NarekA))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2022-03-11&to=2022-03-14&type=c))

[@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2022-03-11..2022-03-14&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2022-03-11..2022-03-14&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2022-03-11..2022-03-14&type=Issues) | [@NarekA](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ANarekA+updated%3A2022-03-11..2022-03-14&type=Issues)

### 2.2.1 2022-03-11

2.2.1 fixes a few small regressions in 2.2.0.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/2.2.0...2.2.1))

#### Bugs fixed

- Fix clearing cookie with custom xsrf cookie options [#3823](https://github.com/jupyterhub/jupyterhub/pull/3823) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Fix admin dashboard table sorting [#3822](https://github.com/jupyterhub/jupyterhub/pull/3822) ([@NarekA](https://github.com/NarekA), [@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Maintenance and upkeep improvements

- allow Spawner.server to be mocked without underlying orm_spawner [#3819](https://github.com/jupyterhub/jupyterhub/pull/3819) ([@minrk](https://github.com/minrk), [@yuvipanda](https://github.com/yuvipanda), [@consideRatio](https://github.com/consideRatio))

#### Documentation

- Add some docs on common log messages [#3820](https://github.com/jupyterhub/jupyterhub/pull/3820) ([@yuvipanda](https://github.com/yuvipanda), [@choldgraf](https://github.com/choldgraf), [@consideRatio](https://github.com/consideRatio))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2022-03-07&to=2022-03-11&type=c))

[@choldgraf](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acholdgraf+updated%3A2022-03-07..2022-03-11&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2022-03-07..2022-03-11&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2022-03-07..2022-03-11&type=Issues) | [@NarekA](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ANarekA+updated%3A2022-03-07..2022-03-11&type=Issues) | [@yuvipanda](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2022-03-07..2022-03-11&type=Issues)

### 2.2.0 2022-03-07

JupyterHub 2.2.0 is a small release.
The main new feature is the ability of Authenticators to [manage group membership](authenticator-groups),
e.g. when the identity provider has its own concept of groups that should be preserved
in JupyterHub.

The links to access user servers from the admin page have been restored.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/2.1.1...2.2.0))

#### New features added

- Enable `options_from_form(spawner, form_data)` signature from configuration file [#3791](https://github.com/jupyterhub/jupyterhub/pull/3791) ([@rcthomas](https://github.com/rcthomas), [@minrk](https://github.com/minrk))
- Authenticator user group management [#3548](https://github.com/jupyterhub/jupyterhub/pull/3548) ([@thomafred](https://github.com/thomafred), [@minrk](https://github.com/minrk))

#### Enhancements made

- Add user token to JupyterLab PageConfig [#3809](https://github.com/jupyterhub/jupyterhub/pull/3809) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics), [@consideRatio](https://github.com/consideRatio))
- show insecure-login-warning for all authenticators [#3793](https://github.com/jupyterhub/jupyterhub/pull/3793) ([@satra](https://github.com/satra), [@minrk](https://github.com/minrk))
- short-circuit token permission check if token and owner share role [#3792](https://github.com/jupyterhub/jupyterhub/pull/3792) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Named server support, access links in admin page [#3790](https://github.com/jupyterhub/jupyterhub/pull/3790) ([@NarekA](https://github.com/NarekA), [@minrk](https://github.com/minrk), [@ykazakov](https://github.com/ykazakov), [@manics](https://github.com/manics))

#### Bugs fixed

- Keep Spawner.server in sync with underlying orm_spawner.server [#3810](https://github.com/jupyterhub/jupyterhub/pull/3810) ([@minrk](https://github.com/minrk), [@manics](https://github.com/manics), [@GeorgianaElena](https://github.com/GeorgianaElena), [@consideRatio](https://github.com/consideRatio))
- Replace failed spawners when starting new launch [#3802](https://github.com/jupyterhub/jupyterhub/pull/3802) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))
- Log proxy's public_url only when started by JupyterHub [#3781](https://github.com/jupyterhub/jupyterhub/pull/3781) ([@cqzlxl](https://github.com/cqzlxl), [@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk))

#### Documentation improvements

- Apache2 Documentation: Updates Reverse Proxy Configuration (TLS/SSL, Protocols, Headers) [#3813](https://github.com/jupyterhub/jupyterhub/pull/3813) ([@rzo1](https://github.com/rzo1), [@minrk](https://github.com/minrk))
- Update example to not reference an undefined scope [#3812](https://github.com/jupyterhub/jupyterhub/pull/3812) ([@ktaletsk](https://github.com/ktaletsk), [@minrk](https://github.com/minrk))
- Apache: set X-Forwarded-Proto header [#3808](https://github.com/jupyterhub/jupyterhub/pull/3808) ([@manics](https://github.com/manics), [@consideRatio](https://github.com/consideRatio), [@rzo1](https://github.com/rzo1), [@tobi45](https://github.com/tobi45))
- idle-culler example config missing closing bracket [#3803](https://github.com/jupyterhub/jupyterhub/pull/3803) ([@tmtabor](https://github.com/tmtabor), [@consideRatio](https://github.com/consideRatio))

#### Behavior Changes

- Stop opening PAM sessions by default [#3787](https://github.com/jupyterhub/jupyterhub/pull/3787) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2022-01-25&to=2022-03-07&type=c))

[@blink1073](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ablink1073+updated%3A2022-01-25..2022-03-07&type=Issues) | [@clkao](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aclkao+updated%3A2022-01-25..2022-03-07&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2022-01-25..2022-03-07&type=Issues) | [@cqzlxl](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acqzlxl+updated%3A2022-01-25..2022-03-07&type=Issues) | [@dependabot](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adependabot+updated%3A2022-01-25..2022-03-07&type=Issues) | [@dtaniwaki](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adtaniwaki+updated%3A2022-01-25..2022-03-07&type=Issues) | [@fcollonval](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Afcollonval+updated%3A2022-01-25..2022-03-07&type=Issues) | [@GeorgianaElena](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AGeorgianaElena+updated%3A2022-01-25..2022-03-07&type=Issues) | [@github-actions](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Agithub-actions+updated%3A2022-01-25..2022-03-07&type=Issues) | [@kshitija08](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akshitija08+updated%3A2022-01-25..2022-03-07&type=Issues) | [@ktaletsk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aktaletsk+updated%3A2022-01-25..2022-03-07&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2022-01-25..2022-03-07&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2022-01-25..2022-03-07&type=Issues) | [@NarekA](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ANarekA+updated%3A2022-01-25..2022-03-07&type=Issues) | [@pre-commit-ci](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apre-commit-ci+updated%3A2022-01-25..2022-03-07&type=Issues) | [@rajat404](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arajat404+updated%3A2022-01-25..2022-03-07&type=Issues) | [@rcthomas](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arcthomas+updated%3A2022-01-25..2022-03-07&type=Issues) | [@ryogesh](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aryogesh+updated%3A2022-01-25..2022-03-07&type=Issues) | [@rzo1](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arzo1+updated%3A2022-01-25..2022-03-07&type=Issues) | [@satra](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asatra+updated%3A2022-01-25..2022-03-07&type=Issues) | [@thomafred](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Athomafred+updated%3A2022-01-25..2022-03-07&type=Issues) | [@tmtabor](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atmtabor+updated%3A2022-01-25..2022-03-07&type=Issues) | [@tobi45](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atobi45+updated%3A2022-01-25..2022-03-07&type=Issues) | [@ykazakov](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aykazakov+updated%3A2022-01-25..2022-03-07&type=Issues)

## 2.1

### 2.1.1 2022-01-25

2.1.1 is a tiny bugfix release,
fixing an issue where admins did not receive the new `read:metrics` permission.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/2.1.0...2.1.1))

#### Bugs fixed

- add missing read:metrics scope to admin role [#3778](https://github.com/jupyterhub/jupyterhub/pull/3778) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2022-01-21&to=2022-01-25&type=c))

[@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2022-01-21..2022-01-25&type=Issues) | [@dependabot](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adependabot+updated%3A2022-01-21..2022-01-25&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2022-01-21..2022-01-25&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2022-01-21..2022-01-25&type=Issues)

### 2.1.0 2022-01-21

2.1.0 is a small bugfix release, resolving regressions in 2.0 and further refinements.
In particular, the authenticated prometheus metrics endpoint did not work in 2.0 because it lacked a scope.
To access the authenticated metrics endpoint with a token,
upgrade to 2.1 and make sure the token/owner has the `read:metrics` scope.

Custom error messages for failed spawns are now handled more consistently on the spawn-progress API and the spawn-failed HTML page.
Previously, spawn-progress did not relay the custom message provided by `exception.jupyterhub_message`,
and full HTML messages in `exception.jupyterhub_html_message` can now be displayed in both contexts.

The long-deprecated, inconsistent behavior when users visited a URL for another user's server,
where they could sometimes be redirected back to their own server,
has been removed in favor of consistent behavior based on the user's permissions.
To share a URL that will take any user to their own server, use `https://my.hub/hub/user-redirect/path/...`.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/2.0.2...2.1.0))

#### Enhancements made

- relay custom messages in exception.jupyterhub_message in progress API [#3764](https://github.com/jupyterhub/jupyterhub/pull/3764) ([@minrk](https://github.com/minrk))
- Add the capability to inform a connection to Alembic Migration Script [#3762](https://github.com/jupyterhub/jupyterhub/pull/3762) ([@DougTrajano](https://github.com/DougTrajano))

#### Bugs fixed

- Fix loading Spawner.user_options from db [#3773](https://github.com/jupyterhub/jupyterhub/pull/3773) ([@IgorBerman](https://github.com/IgorBerman))
- Add missing `read:metrics` scope for authenticated metrics endpoint [#3770](https://github.com/jupyterhub/jupyterhub/pull/3770) ([@minrk](https://github.com/minrk))
- apply scope checks to some admin-or-self situations [#3763](https://github.com/jupyterhub/jupyterhub/pull/3763) ([@minrk](https://github.com/minrk))

#### Maintenance and upkeep improvements

- DOCS: Add github metadata for edit button [#3775](https://github.com/jupyterhub/jupyterhub/pull/3775) ([@minrk](https://github.com/minrk))

#### Documentation improvements

- Improve documentation about spawner exception handling [#3765](https://github.com/jupyterhub/jupyterhub/pull/3765) ([@twalcari](https://github.com/twalcari))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2022-01-10&to=2022-01-21&type=c))

[@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2022-01-10..2022-01-21&type=Issues) | [@dependabot](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adependabot+updated%3A2022-01-10..2022-01-21&type=Issues) | [@DougTrajano](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ADougTrajano+updated%3A2022-01-10..2022-01-21&type=Issues) | [@IgorBerman](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AIgorBerman+updated%3A2022-01-10..2022-01-21&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2022-01-10..2022-01-21&type=Issues) | [@twalcari](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atwalcari+updated%3A2022-01-10..2022-01-21&type=Issues) | [@welcome](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awelcome+updated%3A2022-01-10..2022-01-21&type=Issues)

## 2.0

### [2.0.2] 2022-01-10

2.0.2 fixes a regression in 2.0.1 causing false positives
rejecting valid requests as cross-origin,
mostly when JupyterHub is behind additional proxies.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/2.0.1...2.0.2))

#### Bugs fixed

- use outermost proxied entry when looking up browser protocol [#3757](https://github.com/jupyterhub/jupyterhub/pull/3757) ([@minrk](https://github.com/minrk))

#### Maintenance and upkeep improvements

- remove unused macro with missing references [#3760](https://github.com/jupyterhub/jupyterhub/pull/3760) ([@minrk](https://github.com/minrk))
- ci: refactor to avoid triggering all tests on changes to docs [#3750](https://github.com/jupyterhub/jupyterhub/pull/3750) ([@consideRatio](https://github.com/consideRatio))
- Extra test_cors_check tests [#3746](https://github.com/jupyterhub/jupyterhub/pull/3746) ([@manics](https://github.com/manics))

#### Documentation improvements

- DOCS: Update theme configuration [#3754](https://github.com/jupyterhub/jupyterhub/pull/3754) ([@choldgraf](https://github.com/choldgraf))
- DOC: Add note about allowed_users not being set [#3748](https://github.com/jupyterhub/jupyterhub/pull/3748) ([@choldgraf](https://github.com/choldgraf))
- localhost URL is http, not https [#3747](https://github.com/jupyterhub/jupyterhub/pull/3747) ([@minrk](https://github.com/minrk))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2021-12-22&to=2022-01-10&type=c))

[@choldgraf](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acholdgraf+updated%3A2021-12-22..2022-01-10&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2021-12-22..2022-01-10&type=Issues) | [@github-actions](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Agithub-actions+updated%3A2021-12-22..2022-01-10&type=Issues) | [@jakob-keller](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajakob-keller+updated%3A2021-12-22..2022-01-10&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2021-12-22..2022-01-10&type=Issues) | [@meeseeksmachine](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ameeseeksmachine+updated%3A2021-12-22..2022-01-10&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2021-12-22..2022-01-10&type=Issues) | [@pre-commit-ci](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apre-commit-ci+updated%3A2021-12-22..2022-01-10&type=Issues) | [@welcome](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awelcome+updated%3A2021-12-22..2022-01-10&type=Issues)

### [2.0.1]

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/2.0.0...2.0.1))

2.0.1 is a bugfix release, with some additional small improvements,
especially in the new RBAC handling and admin page.

Several issues are fixed where users might not have the
default 'user' role as expected.

#### Enhancements made

- Use URL from authenticator on default login form [#3723](https://github.com/jupyterhub/jupyterhub/pull/3723) ([@sgaist](https://github.com/sgaist))
- always assign default roles on login [#3722](https://github.com/jupyterhub/jupyterhub/pull/3722) ([@minrk](https://github.com/minrk))
- use intersect_scopes utility to check token permissions [#3705](https://github.com/jupyterhub/jupyterhub/pull/3705) ([@minrk](https://github.com/minrk))
- React Error Handling [#3697](https://github.com/jupyterhub/jupyterhub/pull/3697) ([@naatebarber](https://github.com/naatebarber))
- add option to use a different Host header for referer checks [#3195](https://github.com/jupyterhub/jupyterhub/pull/3195) ([@kylewm](https://github.com/kylewm))

#### Bugs fixed

- initialize new admin users with default roles [#3735](https://github.com/jupyterhub/jupyterhub/pull/3735) ([@minrk](https://github.com/minrk))
- Fix missing f-string modifier [#3733](https://github.com/jupyterhub/jupyterhub/pull/3733) ([@manics](https://github.com/manics))
- accept token auth on `/hub/user/...` [#3731](https://github.com/jupyterhub/jupyterhub/pull/3731) ([@minrk](https://github.com/minrk))
- simplify default role assignment [#3720](https://github.com/jupyterhub/jupyterhub/pull/3720) ([@minrk](https://github.com/minrk))
- fix Spawner.oauth_roles config [#3717](https://github.com/jupyterhub/jupyterhub/pull/3717) ([@minrk](https://github.com/minrk))
- Fix error message about Authenticator.pre_spawn_start [#3716](https://github.com/jupyterhub/jupyterhub/pull/3716) ([@minrk](https://github.com/minrk))
- admin: Pass Base Url [#3715](https://github.com/jupyterhub/jupyterhub/pull/3715) ([@naatebarber](https://github.com/naatebarber))
- Grant role after user creation during config load [#3714](https://github.com/jupyterhub/jupyterhub/pull/3714) ([@a3626a](https://github.com/a3626a))
- Avoid clearing user role membership when defining custom user scopes [#3708](https://github.com/jupyterhub/jupyterhub/pull/3708) ([@minrk](https://github.com/minrk))
- cors: handle mismatched implicit/explicit ports in host header [#3701](https://github.com/jupyterhub/jupyterhub/pull/3701) ([@minrk](https://github.com/minrk))

#### Maintenance and upkeep improvements

- clarify `role` argument in grant/strip_role [#3727](https://github.com/jupyterhub/jupyterhub/pull/3727) ([@minrk](https://github.com/minrk))
- check for db clients before requesting install [#3719](https://github.com/jupyterhub/jupyterhub/pull/3719) ([@minrk](https://github.com/minrk))
- run jsx tests in their own job [#3698](https://github.com/jupyterhub/jupyterhub/pull/3698) ([@minrk](https://github.com/minrk))

#### Documentation improvements

- update service-whoami example [#3726](https://github.com/jupyterhub/jupyterhub/pull/3726) ([@minrk](https://github.com/minrk))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2021-12-01&to=2021-12-22&type=c))

[@a3626a](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aa3626a+updated%3A2021-12-01..2021-12-22&type=Issues) | [@betatim](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abetatim+updated%3A2021-12-01..2021-12-22&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2021-12-01..2021-12-22&type=Issues) | [@github-actions](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Agithub-actions+updated%3A2021-12-01..2021-12-22&type=Issues) | [@kylewm](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akylewm+updated%3A2021-12-01..2021-12-22&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2021-12-01..2021-12-22&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2021-12-01..2021-12-22&type=Issues) | [@naatebarber](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Anaatebarber+updated%3A2021-12-01..2021-12-22&type=Issues) | [@pre-commit-ci](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apre-commit-ci+updated%3A2021-12-01..2021-12-22&type=Issues) | [@sgaist](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asgaist+updated%3A2021-12-01..2021-12-22&type=Issues) | [@welcome](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awelcome+updated%3A2021-12-01..2021-12-22&type=Issues)

### [2.0.0]

JupyterHub 2.0 is a big release!

The most significant change is the addition of [roles and scopes](rbac)
to the JupyterHub permissions model,
allowing more fine-grained access control.
Read more about it [in the docs](rbac).

In particular, the 'admin' level of permissions should not be needed anymore,
and you can now grant users and services only the permissions they need, not more.
We encourage you to review permissions, especially any service or user with `admin: true`
and consider assigning only the necessary roles and scopes.

[rbac]: ./rbac/index.md

JupyterHub 2.0 requires an update to the database schema,
so **make sure to [read the upgrade documentation and backup your database](howto:upgrading-jupyterhub)
before upgrading**.

:::{admonition} stop all servers before upgrading
Upgrading JupyterHub to 2.0 revokes all tokens issued before the upgrade,
which means that single-user servers started before the upgrade
will become inaccessible after the upgrade until they have been stopped and started again.
To avoid this, it is best to shutdown all servers prior to the upgrade.
:::

Other major changes that may require updates to your deployment,
depending on what features you use:

- List endpoints now support [pagination][], and have a max page size,
  which means API consumers must be updated to make paginated requests
  if you have a lot of users and/or groups.
- Spawners have stopped specifying _any_ command-line options to spawners by default.
  Previously, `--ip` and `--port` could be specified on the command-line.
  From 2.0 forward, JupyterHub will only communicate options to Spawners via environment variables,
  and the command to be launched is configured exclusively via `Spawner.cmd` and `Spawner.args`.

[pagination]: api-pagination

Other new features:

- new Admin page, written in React.
  With RBAC, it should now be fully possible to implement a custom admin panel
  as a service via the REST API.
- JupyterLab is the default UI for single-user servers,
  if available in the user environment.
  See [more info](classic-notebook-ui)
  in the docs about switching back to the classic notebook,
  if you are not ready to switch to JupyterLab.
- NullAuthenticator is now bundled with JupyterHub,
  so you no longer need to install the `nullauthenticator` package to disable login,
  you can set `c.JupyterHub.authenticator_class = 'null'`.
- Support `jupyterhub --show-config` option to see your current jupyterhub configuration.
- Add expiration date dropdown to Token page

and major bug fixes:

- Improve database rollback recovery on broken connections

and other changes:

- Requests to a not-running server (e.g. visiting `/user/someuser/`)
  will return an HTTP 424 error instead of 503,
  making it easier to monitor for real deployment problems.
  JupyterLab in the user environment should be at least version 3.1.16
  to recognize this error code as a stopped server.
  You can temporarily opt-in to the older behavior (e.g. if older JupyterLab is required)
  by setting `c.JupyterHub.use_legacy_stopped_server_status_code = True`.

Plus lots of little fixes along the way.

### 2.0.0 - 2021-12-01

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/1.5.0...2.0.0))

#### New features added

- Add NullAuthenticator to jupyterhub [#3619](https://github.com/jupyterhub/jupyterhub/pull/3619) ([@manics](https://github.com/manics))
- 2.0: jupyterlab by default [#3615](https://github.com/jupyterhub/jupyterhub/pull/3615) ([@minrk](https://github.com/minrk))
- support inherited `--show-config` flags from base Application [#3559](https://github.com/jupyterhub/jupyterhub/pull/3559) ([@minrk](https://github.com/minrk))
- Add expiration date dropdown to Token page [#3552](https://github.com/jupyterhub/jupyterhub/pull/3552) ([@dolfinus](https://github.com/dolfinus))
- add opt-in model for paginated list results [#3535](https://github.com/jupyterhub/jupyterhub/pull/3535) ([@minrk](https://github.com/minrk))
- Support auto login when used as a OAuth2 provider [#3488](https://github.com/jupyterhub/jupyterhub/pull/3488) ([@yuvipanda](https://github.com/yuvipanda))
- Roles and Scopes (RBAC) [#3438](https://github.com/jupyterhub/jupyterhub/pull/3438) ([@minrk](https://github.com/minrk))
- Make JupyterHub Admin page into a React app [#3398](https://github.com/jupyterhub/jupyterhub/pull/3398) ([@naatebarber](https://github.com/naatebarber))
- Stop specifying `--ip` and `--port` on the command-line [#3381](https://github.com/jupyterhub/jupyterhub/pull/3381) ([@minrk](https://github.com/minrk))

#### Enhancements made

- Add Session id to token/identify models [#3685](https://github.com/jupyterhub/jupyterhub/pull/3685) ([@minrk](https://github.com/minrk))
- Log single-user app versions at startup [#3681](https://github.com/jupyterhub/jupyterhub/pull/3681) ([@minrk](https://github.com/minrk))
- create groups declared in roles [#3664](https://github.com/jupyterhub/jupyterhub/pull/3664) ([@minrk](https://github.com/minrk))
- Fail suspected API requests with 424, not 503 [#3636](https://github.com/jupyterhub/jupyterhub/pull/3636) ([@yuvipanda](https://github.com/yuvipanda))
- add delete scopes for users, groups, servers [#3616](https://github.com/jupyterhub/jupyterhub/pull/3616) ([@minrk](https://github.com/minrk))
- Reduce logging verbosity of 'checking routes' [#3604](https://github.com/jupyterhub/jupyterhub/pull/3604) ([@yuvipanda](https://github.com/yuvipanda))
- Remove a couple every-request debug statements [#3582](https://github.com/jupyterhub/jupyterhub/pull/3582) ([@minrk](https://github.com/minrk))
- Validate Content-Type Header for api POST requests [#3575](https://github.com/jupyterhub/jupyterhub/pull/3575) ([@VaishnaviHire](https://github.com/VaishnaviHire))
- Improved Grammar for the Documentation [#3572](https://github.com/jupyterhub/jupyterhub/pull/3572) ([@eruditehassan](https://github.com/eruditehassan))

#### Bugs fixed

- Hub: only accept tokens in API requests [#3686](https://github.com/jupyterhub/jupyterhub/pull/3686) ([@minrk](https://github.com/minrk))
- Forward-port fixes from 1.5.0 security release [#3679](https://github.com/jupyterhub/jupyterhub/pull/3679) ([@minrk](https://github.com/minrk))
- raise 404 on admin attempt to spawn nonexistent user [#3653](https://github.com/jupyterhub/jupyterhub/pull/3653) ([@minrk](https://github.com/minrk))
- new user token returns 200 instead of 201 [#3646](https://github.com/jupyterhub/jupyterhub/pull/3646) ([@joegasewicz](https://github.com/joegasewicz))
- Added base_url to path for jupyterhub-session-id cookie [#3625](https://github.com/jupyterhub/jupyterhub/pull/3625) ([@albertmichaelj](https://github.com/albertmichaelj))
- Fix wrong name of auth_state_hook in the exception log [#3569](https://github.com/jupyterhub/jupyterhub/pull/3569) ([@dolfinus](https://github.com/dolfinus))
- Stop injecting statsd parameters into the configurable HTTP proxy [#3568](https://github.com/jupyterhub/jupyterhub/pull/3568) ([@paccorsi](https://github.com/paccorsi))
- explicit DB rollback for 500 errors [#3566](https://github.com/jupyterhub/jupyterhub/pull/3566) ([@nsshah1288](https://github.com/nsshah1288))
- don't omit server model if it's empty [#3564](https://github.com/jupyterhub/jupyterhub/pull/3564) ([@minrk](https://github.com/minrk))
- ensure admin requests for missing users 404 [#3563](https://github.com/jupyterhub/jupyterhub/pull/3563) ([@minrk](https://github.com/minrk))
- Avoid zombie processes in case of using LocalProcessSpawner [#3543](https://github.com/jupyterhub/jupyterhub/pull/3543) ([@dolfinus](https://github.com/dolfinus))
- Fix regression where external services api_token became required [#3531](https://github.com/jupyterhub/jupyterhub/pull/3531) ([@consideRatio](https://github.com/consideRatio))
- Fix allow_all check when only allow_admin is set [#3526](https://github.com/jupyterhub/jupyterhub/pull/3526) ([@dolfinus](https://github.com/dolfinus))
- Bug: save_bearer_token (provider.py) passes a float value to the expires_at field (int) [#3484](https://github.com/jupyterhub/jupyterhub/pull/3484) ([@weisdd](https://github.com/weisdd))

#### Maintenance and upkeep improvements

- build jupyterhub/singleuser along with other images [#3690](https://github.com/jupyterhub/jupyterhub/pull/3690) ([@minrk](https://github.com/minrk))
- always use relative paths in data_files [#3682](https://github.com/jupyterhub/jupyterhub/pull/3682) ([@minrk](https://github.com/minrk))
- Forward-port fixes from 1.5.0 security release [#3679](https://github.com/jupyterhub/jupyterhub/pull/3679) ([@minrk](https://github.com/minrk))
- verify that successful login assigns default role [#3674](https://github.com/jupyterhub/jupyterhub/pull/3674) ([@minrk](https://github.com/minrk))
- more calculators [#3673](https://github.com/jupyterhub/jupyterhub/pull/3673) ([@minrk](https://github.com/minrk))
- use v2 of jupyterhub/action-major-minor-tag-calculator [#3672](https://github.com/jupyterhub/jupyterhub/pull/3672) ([@minrk](https://github.com/minrk))
- Add support-bot [#3670](https://github.com/jupyterhub/jupyterhub/pull/3670) ([@manics](https://github.com/manics))
- use tbump to tag versions [#3669](https://github.com/jupyterhub/jupyterhub/pull/3669) ([@minrk](https://github.com/minrk))
- use stable autodoc-traits [#3667](https://github.com/jupyterhub/jupyterhub/pull/3667) ([@minrk](https://github.com/minrk))
- Tests for our openapi spec [#3665](https://github.com/jupyterhub/jupyterhub/pull/3665) ([@minrk](https://github.com/minrk))
- clarify some log messages during role assignment [#3663](https://github.com/jupyterhub/jupyterhub/pull/3663) ([@minrk](https://github.com/minrk))
- Rename 'all' metascope to more descriptive 'inherit' [#3661](https://github.com/jupyterhub/jupyterhub/pull/3661) ([@minrk](https://github.com/minrk))
- minor refinement of excessive scopes error message [#3660](https://github.com/jupyterhub/jupyterhub/pull/3660) ([@minrk](https://github.com/minrk))
- deprecate instead of remove `@admin_only` auth decorator [#3659](https://github.com/jupyterhub/jupyterhub/pull/3659) ([@minrk](https://github.com/minrk))
- improve timeout handling and messages [#3658](https://github.com/jupyterhub/jupyterhub/pull/3658) ([@minrk](https://github.com/minrk))
- add api-only doc [#3640](https://github.com/jupyterhub/jupyterhub/pull/3640) ([@minrk](https://github.com/minrk))
- Add pyupgrade --py36-plus to pre-commit config [#3586](https://github.com/jupyterhub/jupyterhub/pull/3586) ([@consideRatio](https://github.com/consideRatio))
- pyupgrade: run pyupgrade --py36-plus and black on all but tests [#3585](https://github.com/jupyterhub/jupyterhub/pull/3585) ([@consideRatio](https://github.com/consideRatio))
- pyupgrade: run pyupgrade --py36-plus and black on jupyterhub/tests [#3584](https://github.com/jupyterhub/jupyterhub/pull/3584) ([@consideRatio](https://github.com/consideRatio))
- remove use of deprecated distutils [#3562](https://github.com/jupyterhub/jupyterhub/pull/3562) ([@minrk](https://github.com/minrk))
- remove old, unused tasks.py [#3561](https://github.com/jupyterhub/jupyterhub/pull/3561) ([@minrk](https://github.com/minrk))
- remove very old backward-compat for LocalProcess subclasses [#3558](https://github.com/jupyterhub/jupyterhub/pull/3558) ([@minrk](https://github.com/minrk))
- Remove pre-commit from GHA [#3524](https://github.com/jupyterhub/jupyterhub/pull/3524) ([@minrk](https://github.com/minrk))
- bump autodoc-traits [#3510](https://github.com/jupyterhub/jupyterhub/pull/3510) ([@minrk](https://github.com/minrk))
- release docker workflow: 'branchRegex: ^\w[\w-.]\*$' [#3509](https://github.com/jupyterhub/jupyterhub/pull/3509) ([@manics](https://github.com/manics))
- exclude dependabot push events from release workflow [#3505](https://github.com/jupyterhub/jupyterhub/pull/3505) ([@minrk](https://github.com/minrk))
- prepare to rename default branch to main [#3462](https://github.com/jupyterhub/jupyterhub/pull/3462) ([@minrk](https://github.com/minrk))

#### Documentation improvements

- Service auth doc [#3695](https://github.com/jupyterhub/jupyterhub/pull/3695) ([@minrk](https://github.com/minrk))
- changelog for 2.0.0rc5 [#3692](https://github.com/jupyterhub/jupyterhub/pull/3692) ([@minrk](https://github.com/minrk))
- update 2.0 changelog [#3687](https://github.com/jupyterhub/jupyterhub/pull/3687) ([@minrk](https://github.com/minrk))
- changelog for 2.0 release candidate [#3662](https://github.com/jupyterhub/jupyterhub/pull/3662) ([@minrk](https://github.com/minrk))
- docs: fix typo in proxy config example [#3657](https://github.com/jupyterhub/jupyterhub/pull/3657) ([@edgarcosta](https://github.com/edgarcosta))
- add 424 status code change to changelog [#3649](https://github.com/jupyterhub/jupyterhub/pull/3649) ([@minrk](https://github.com/minrk))
- add latest changes to 2.0 changelog [#3628](https://github.com/jupyterhub/jupyterhub/pull/3628) ([@minrk](https://github.com/minrk))
- server-api example typo: trim space in token file [#3626](https://github.com/jupyterhub/jupyterhub/pull/3626) ([@minrk](https://github.com/minrk))
- Fix heading level in changelog [#3610](https://github.com/jupyterhub/jupyterhub/pull/3610) ([@mriedem](https://github.com/mriedem))
- update quickstart requirements [#3607](https://github.com/jupyterhub/jupyterhub/pull/3607) ([@minrk](https://github.com/minrk))
- 2.0 changelog [#3602](https://github.com/jupyterhub/jupyterhub/pull/3602) ([@minrk](https://github.com/minrk))
- Update/cleanup README [#3601](https://github.com/jupyterhub/jupyterhub/pull/3601) ([@manics](https://github.com/manics))
- mailto link typo [#3593](https://github.com/jupyterhub/jupyterhub/pull/3593) ([@minrk](https://github.com/minrk))
- [doc] add example specifying scopes for a default role [#3581](https://github.com/jupyterhub/jupyterhub/pull/3581) ([@minrk](https://github.com/minrk))
- Add detailed doc for starting/waiting for servers via api [#3565](https://github.com/jupyterhub/jupyterhub/pull/3565) ([@minrk](https://github.com/minrk))
- doc: Mention a list of known proxies available [#3546](https://github.com/jupyterhub/jupyterhub/pull/3546) ([@AbdealiJK](https://github.com/AbdealiJK))
- Update changelog for 1.4.2 in main branch [#3539](https://github.com/jupyterhub/jupyterhub/pull/3539) ([@consideRatio](https://github.com/consideRatio))
- Retrospectively update changelog for 1.4.1 in main branch [#3537](https://github.com/jupyterhub/jupyterhub/pull/3537) ([@consideRatio](https://github.com/consideRatio))
- Fix contributor documentation's link [#3521](https://github.com/jupyterhub/jupyterhub/pull/3521) ([@icankeep](https://github.com/icankeep))
- Add research study participation notice to readme [#3506](https://github.com/jupyterhub/jupyterhub/pull/3506) ([@sgibson91](https://github.com/sgibson91))
- Fix typo [#3494](https://github.com/jupyterhub/jupyterhub/pull/3494) ([@davidbrochart](https://github.com/davidbrochart))
- Add Chameleon to JupyterHub deployment gallery [#3482](https://github.com/jupyterhub/jupyterhub/pull/3482) ([@diurnalist](https://github.com/diurnalist))
- Initial SECURITY.md [#3445](https://github.com/jupyterhub/jupyterhub/pull/3445) ([@rpwagner](https://github.com/rpwagner))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2021-04-19&to=2021-11-30&type=c))

[@0mar](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3A0mar+updated%3A2021-04-19..2021-11-30&type=Issues) | [@AbdealiJK](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AAbdealiJK+updated%3A2021-04-19..2021-11-30&type=Issues) | [@albertmichaelj](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aalbertmichaelj+updated%3A2021-04-19..2021-11-30&type=Issues) | [@betatim](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abetatim+updated%3A2021-04-19..2021-11-30&type=Issues) | [@bollwyvl](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abollwyvl+updated%3A2021-04-19..2021-11-30&type=Issues) | [@choldgraf](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acholdgraf+updated%3A2021-04-19..2021-11-30&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2021-04-19..2021-11-30&type=Issues) | [@cslocum](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acslocum+updated%3A2021-04-19..2021-11-30&type=Issues) | [@danlester](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adanlester+updated%3A2021-04-19..2021-11-30&type=Issues) | [@davidbrochart](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adavidbrochart+updated%3A2021-04-19..2021-11-30&type=Issues) | [@dependabot](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adependabot+updated%3A2021-04-19..2021-11-30&type=Issues) | [@diurnalist](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adiurnalist+updated%3A2021-04-19..2021-11-30&type=Issues) | [@dolfinus](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adolfinus+updated%3A2021-04-19..2021-11-30&type=Issues) | [@echarles](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aecharles+updated%3A2021-04-19..2021-11-30&type=Issues) | [@edgarcosta](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aedgarcosta+updated%3A2021-04-19..2021-11-30&type=Issues) | [@ellisonbg](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aellisonbg+updated%3A2021-04-19..2021-11-30&type=Issues) | [@eruditehassan](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aeruditehassan+updated%3A2021-04-19..2021-11-30&type=Issues) | [@icankeep](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aicankeep+updated%3A2021-04-19..2021-11-30&type=Issues) | [@IvanaH8](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AIvanaH8+updated%3A2021-04-19..2021-11-30&type=Issues) | [@joegasewicz](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajoegasewicz+updated%3A2021-04-19..2021-11-30&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2021-04-19..2021-11-30&type=Issues) | [@meeseeksmachine](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ameeseeksmachine+updated%3A2021-04-19..2021-11-30&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2021-04-19..2021-11-30&type=Issues) | [@mriedem](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amriedem+updated%3A2021-04-19..2021-11-30&type=Issues) | [@naatebarber](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Anaatebarber+updated%3A2021-04-19..2021-11-30&type=Issues) | [@nsshah1288](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ansshah1288+updated%3A2021-04-19..2021-11-30&type=Issues) | [@octavd](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aoctavd+updated%3A2021-04-19..2021-11-30&type=Issues) | [@OrnithOrtion](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AOrnithOrtion+updated%3A2021-04-19..2021-11-30&type=Issues) | [@paccorsi](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apaccorsi+updated%3A2021-04-19..2021-11-30&type=Issues) | [@panruipr](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apanruipr+updated%3A2021-04-19..2021-11-30&type=Issues) | [@pre-commit-ci](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apre-commit-ci+updated%3A2021-04-19..2021-11-30&type=Issues) | [@rpwagner](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arpwagner+updated%3A2021-04-19..2021-11-30&type=Issues) | [@sgibson91](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asgibson91+updated%3A2021-04-19..2021-11-30&type=Issues) | [@support](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asupport+updated%3A2021-04-19..2021-11-30&type=Issues) | [@twalcari](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atwalcari+updated%3A2021-04-19..2021-11-30&type=Issues) | [@VaishnaviHire](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AVaishnaviHire+updated%3A2021-04-19..2021-11-30&type=Issues) | [@warwing](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awarwing+updated%3A2021-04-19..2021-11-30&type=Issues) | [@weisdd](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aweisdd+updated%3A2021-04-19..2021-11-30&type=Issues) | [@welcome](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awelcome+updated%3A2021-04-19..2021-11-30&type=Issues) | [@willingc](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awillingc+updated%3A2021-04-19..2021-11-30&type=Issues) | [@ykazakov](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aykazakov+updated%3A2021-04-19..2021-11-30&type=Issues) | [@yuvipanda](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2021-04-19..2021-11-30&type=Issues)

## 1.5

JupyterHub 1.5 is a **security release**,
fixing a vulnerability [ghsa-cw7p-q79f-m2v7][] where JupyterLab users
with multiple tabs open could fail to logout completely,
leaving their browser with valid credentials until they logout again.

A few fully backward-compatible features have been backported from 2.0.

[ghsa-cw7p-q79f-m2v7]: https://github.com/jupyterhub/jupyterhub/security/advisories/GHSA-cw7p-q79f-m2v7

### 1.5.1 2022-12-05

This is a patch release, improving db resiliency when certain errors occur, without requiring a jupyterhub restart.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/1.5.0...1.5.1))

#### Merged PRs

- Backport db rollback fixes to 1.x [#4076](https://github.com/jupyterhub/jupyterhub/pull/4076) ([@mriedem](https://github.com/mriedem), [@minrk](https://github.com/minrk)), [@nsshah1288](https://github.com/nsshah1288)

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2022-09-09&to=2022-11-30&type=c))

[@mriedem](https://github.com/mriedem) | [@minrk](https://github.com/minrk) | [@nsshah1288](https://github.com/nsshah1288)

### [1.5.0] 2021-11-04

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/1.4.2...1.5.0))

#### New features added

- Backport #3636 to 1.4.x (opt-in support for JupyterHub.use_legacy_stopped_server_status_code) [#3639](https://github.com/jupyterhub/jupyterhub/pull/3639) ([@yuvipanda](https://github.com/yuvipanda))
- Backport PR #3552 on branch 1.4.x (Add expiration date dropdown to Token page) [#3580](https://github.com/jupyterhub/jupyterhub/pull/3580) ([@meeseeksmachine](https://github.com/meeseeksmachine))
- Backport PR #3488 on branch 1.4.x (Support auto login when used as a OAuth2 provider) [#3579](https://github.com/jupyterhub/jupyterhub/pull/3579) ([@meeseeksmachine](https://github.com/meeseeksmachine))

#### Maintenance and upkeep improvements

- 1.4.x: update doc requirements [#3677](https://github.com/jupyterhub/jupyterhub/pull/3677) ([@minrk](https://github.com/minrk))

#### Documentation improvements

- use_legacy_stopped_server_status_code: use 1.\* language [#3676](https://github.com/jupyterhub/jupyterhub/pull/3676) ([@manics](https://github.com/manics))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2021-07-16&to=2021-11-03&type=c))

[@choldgraf](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acholdgraf+updated%3A2021-07-16..2021-11-03&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2021-07-16..2021-11-03&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2021-07-16..2021-11-03&type=Issues) | [@meeseeksmachine](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ameeseeksmachine+updated%3A2021-07-16..2021-11-03&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2021-07-16..2021-11-03&type=Issues) | [@support](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asupport+updated%3A2021-07-16..2021-11-03&type=Issues) | [@welcome](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awelcome+updated%3A2021-07-16..2021-11-03&type=Issues) | [@yuvipanda](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2021-07-16..2021-11-03&type=Issues)

## 1.4

JupyterHub 1.4 is a small release, with several enhancements, bug fixes,
and new configuration options.

There are no database schema changes requiring migration from 1.3 to 1.4.

1.4 is also the first version to start publishing docker images for arm64.

In particular, OAuth tokens stored in user cookies,
used for accessing single-user servers and hub-authenticated services,
have changed their expiration from one hour to the expiry of the cookie
in which they are stored (default: two weeks).
This is now also configurable via `JupyterHub.oauth_token_expires_in`.

The result is that it should be much less likely for auth tokens stored in cookies
to expire during the lifetime of a server.

### [1.4.2] 2021-06-15

1.4.2 is a small bugfix release for 1.4.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/1.4.1...d9860aa98cc537cf685022f81b8f725bfef41304))

#### Bugs fixed

- Fix regression where external services api_token became required [#3531](https://github.com/jupyterhub/jupyterhub/pull/3531) ([@consideRatio](https://github.com/consideRatio))
- Bug: save_bearer_token (provider.py) passes a float value to the expires_at field (int) [#3484](https://github.com/jupyterhub/jupyterhub/pull/3484) ([@weisdd](https://github.com/weisdd))

#### Maintenance and upkeep improvements

- bump autodoc-traits [#3510](https://github.com/jupyterhub/jupyterhub/pull/3510) ([@minrk](https://github.com/minrk))

#### Documentation improvements

- Fix contributor documentation's link [#3521](https://github.com/jupyterhub/jupyterhub/pull/3521) ([@icankeep](https://github.com/icankeep))
- Fix typo [#3494](https://github.com/jupyterhub/jupyterhub/pull/3494) ([@davidbrochart](https://github.com/davidbrochart))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2021-05-12&to=2021-07-15&type=c))

[@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2021-05-12..2021-07-15&type=Issues) | [@davidbrochart](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adavidbrochart+updated%3A2021-05-12..2021-07-15&type=Issues) | [@icankeep](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aicankeep+updated%3A2021-05-12..2021-07-15&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2021-05-12..2021-07-15&type=Issues) | [@weisdd](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aweisdd+updated%3A2021-05-12..2021-07-15&type=Issues)

### [1.4.1] 2021-05-12

1.4.1 is a small bugfix release for 1.4.

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/1.4.0...1.4.1))

#### Enhancements made

#### Bugs fixed

- define Spawner.delete_forever on base Spawner [#3454](https://github.com/jupyterhub/jupyterhub/pull/3454) ([@minrk](https://github.com/minrk))
- patch base handlers from both jupyter_server and notebook [#3437](https://github.com/jupyterhub/jupyterhub/pull/3437) ([@minrk](https://github.com/minrk))

#### Maintenance and upkeep improvements

- ci: fix typo in environment variable [#3457](https://github.com/jupyterhub/jupyterhub/pull/3457) ([@consideRatio](https://github.com/consideRatio))
- avoid re-using asyncio.Locks across event loops [#3456](https://github.com/jupyterhub/jupyterhub/pull/3456) ([@minrk](https://github.com/minrk))
- ci: github workflow security, pin action to sha etc [#3436](https://github.com/jupyterhub/jupyterhub/pull/3436) ([@consideRatio](https://github.com/consideRatio))

#### Documentation improvements

- Fix documentation [#3452](https://github.com/jupyterhub/jupyterhub/pull/3452) ([@davidbrochart](https://github.com/davidbrochart))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2021-04-19&to=2021-05-12&type=c))

[@0mar](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3A0mar+updated%3A2021-04-19..2021-05-12&type=Issues) | [@betatim](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abetatim+updated%3A2021-04-19..2021-05-12&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2021-04-19..2021-05-12&type=Issues) | [@danlester](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adanlester+updated%3A2021-04-19..2021-05-12&type=Issues) | [@davidbrochart](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adavidbrochart+updated%3A2021-04-19..2021-05-12&type=Issues) | [@IvanaH8](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AIvanaH8+updated%3A2021-04-19..2021-05-12&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2021-04-19..2021-05-12&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2021-04-19..2021-05-12&type=Issues) | [@naatebarber](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Anaatebarber+updated%3A2021-04-19..2021-05-12&type=Issues) | [@OrnithOrtion](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AOrnithOrtion+updated%3A2021-04-19..2021-05-12&type=Issues) | [@support](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asupport+updated%3A2021-04-19..2021-05-12&type=Issues) | [@welcome](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awelcome+updated%3A2021-04-19..2021-05-12&type=Issues)

### [1.4.0] 2021-04-19

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/1.3.0...1.4.0))

#### New features added

- Support Proxy.extra_routes [#3430](https://github.com/jupyterhub/jupyterhub/pull/3430) ([@yuvipanda](https://github.com/yuvipanda))
- login-template: Add a "login_container" block inside the div-container. [#3422](https://github.com/jupyterhub/jupyterhub/pull/3422) ([@olifre](https://github.com/olifre))
- Docker arm64 builds [#3421](https://github.com/jupyterhub/jupyterhub/pull/3421) ([@manics](https://github.com/manics))
- make oauth token expiry configurable [#3411](https://github.com/jupyterhub/jupyterhub/pull/3411) ([@minrk](https://github.com/minrk))
- allow the hub to not be the default route [#3373](https://github.com/jupyterhub/jupyterhub/pull/3373) ([@minrk](https://github.com/minrk))
- Allow customization of service menu via templates [#3345](https://github.com/jupyterhub/jupyterhub/pull/3345) ([@stv0g](https://github.com/stv0g))
- Add Spawner.delete_forever [#3337](https://github.com/jupyterhub/jupyterhub/pull/3337) ([@nsshah1288](https://github.com/nsshah1288))
- Allow to set spawner-specific hub connect URL [#3326](https://github.com/jupyterhub/jupyterhub/pull/3326) ([@dtaniwaki](https://github.com/dtaniwaki))
- Make Authenticator Custom HTML Flexible [#3315](https://github.com/jupyterhub/jupyterhub/pull/3315) ([@dtaniwaki](https://github.com/dtaniwaki))

#### Enhancements made

- Log the exception raised in Spawner.post_stop_hook instead of raising it [#3418](https://github.com/jupyterhub/jupyterhub/pull/3418) ([@jiajunjie](https://github.com/jiajunjie))
- Don't delete all oauth clients on startup [#3407](https://github.com/jupyterhub/jupyterhub/pull/3407) ([@yuvipanda](https://github.com/yuvipanda))
- Use 'secrets' module to generate secrets [#3394](https://github.com/jupyterhub/jupyterhub/pull/3394) ([@yuvipanda](https://github.com/yuvipanda))
- Allow cookie_secret to be set to a hexadecimal string [#3343](https://github.com/jupyterhub/jupyterhub/pull/3343) ([@consideRatio](https://github.com/consideRatio))
- Clear tornado xsrf cookie on logout [#3341](https://github.com/jupyterhub/jupyterhub/pull/3341) ([@dtaniwaki](https://github.com/dtaniwaki))
- always log slow requests at least at info-level [#3338](https://github.com/jupyterhub/jupyterhub/pull/3338) ([@minrk](https://github.com/minrk))

#### Bugs fixed

- always start redirect count at 1 when redirecting /hub/user/:name -> /user/:name [#3377](https://github.com/jupyterhub/jupyterhub/pull/3377) ([@minrk](https://github.com/minrk))
- Always raise on failed token creation [#3370](https://github.com/jupyterhub/jupyterhub/pull/3370) ([@minrk](https://github.com/minrk))
- make_singleuser_app: patch-in HubAuthenticatedHandler at lower priority [#3347](https://github.com/jupyterhub/jupyterhub/pull/3347) ([@minrk](https://github.com/minrk))
- Fix pagination with named servers [#3335](https://github.com/jupyterhub/jupyterhub/pull/3335) ([@rcthomas](https://github.com/rcthomas))

#### Maintenance and upkeep improvements

- typos in onbuild, demo images for push [#3429](https://github.com/jupyterhub/jupyterhub/pull/3429) ([@minrk](https://github.com/minrk))
- Disable docker jupyterhub-demo arm64 build [#3425](https://github.com/jupyterhub/jupyterhub/pull/3425) ([@manics](https://github.com/manics))
- Docker arm64 builds [#3421](https://github.com/jupyterhub/jupyterhub/pull/3421) ([@manics](https://github.com/manics))
- avoid deprecated engine.table_names [#3392](https://github.com/jupyterhub/jupyterhub/pull/3392) ([@minrk](https://github.com/minrk))
- alpine dockerfile: avoid compilation by getting some deps from apk [#3386](https://github.com/jupyterhub/jupyterhub/pull/3386) ([@minrk](https://github.com/minrk))
- Fix sqlachemy.interfaces.PoolListener deprecation for tests [#3383](https://github.com/jupyterhub/jupyterhub/pull/3383) ([@IvanaH8](https://github.com/IvanaH8))
- Update pre-commit hooks versions [#3362](https://github.com/jupyterhub/jupyterhub/pull/3362) ([@consideRatio](https://github.com/consideRatio))
- add (and run) prettier pre-commit hook [#3360](https://github.com/jupyterhub/jupyterhub/pull/3360) ([@minrk](https://github.com/minrk))
- move get_custom_html to base Authenticator class [#3359](https://github.com/jupyterhub/jupyterhub/pull/3359) ([@minrk](https://github.com/minrk))
- publish release outputs as artifacts [#3349](https://github.com/jupyterhub/jupyterhub/pull/3349) ([@minrk](https://github.com/minrk))
- [TST] Do not implicitly create users in auth_header [#3344](https://github.com/jupyterhub/jupyterhub/pull/3344) ([@minrk](https://github.com/minrk))
- specify minimum alembic 1.4 [#3339](https://github.com/jupyterhub/jupyterhub/pull/3339) ([@minrk](https://github.com/minrk))
- ci: github actions, allow for manual test runs and fix badge in readme [#3324](https://github.com/jupyterhub/jupyterhub/pull/3324) ([@consideRatio](https://github.com/consideRatio))
- publish releases from github actions [#3305](https://github.com/jupyterhub/jupyterhub/pull/3305) ([@minrk](https://github.com/minrk))

#### Documentation improvements

- DOC: Conform to numpydoc. [#3428](https://github.com/jupyterhub/jupyterhub/pull/3428) ([@Carreau](https://github.com/Carreau))
- Fix link to jupyterhub/jupyterhub-the-hard-way [#3417](https://github.com/jupyterhub/jupyterhub/pull/3417) ([@manics](https://github.com/manics))
- Changelog for 1.4 [#3415](https://github.com/jupyterhub/jupyterhub/pull/3415) ([@minrk](https://github.com/minrk))
- Fastapi example [#3403](https://github.com/jupyterhub/jupyterhub/pull/3403) ([@kafonek](https://github.com/kafonek))
- Added Azure AD as a supported authenticator. [#3401](https://github.com/jupyterhub/jupyterhub/pull/3401) ([@maxshowarth](https://github.com/maxshowarth))
- Remove the hard way guide [#3375](https://github.com/jupyterhub/jupyterhub/pull/3375) ([@manics](https://github.com/manics))
- :memo: Fix telemetry section [#3333](https://github.com/jupyterhub/jupyterhub/pull/3333) ([@trallard](https://github.com/trallard))
- Fix the help related to the proxy check [#3332](https://github.com/jupyterhub/jupyterhub/pull/3332) ([@jiajunjie](https://github.com/jiajunjie))
- Mention Jupyter Server as optional single-user backend in documentation [#3329](https://github.com/jupyterhub/jupyterhub/pull/3329) ([@Zsailer](https://github.com/Zsailer))
- Fix mixup in comment regarding the sync parameter [#3325](https://github.com/jupyterhub/jupyterhub/pull/3325) ([@andrewisplinghoff](https://github.com/andrewisplinghoff))
- docs: fix simple typo, funciton -> function [#3314](https://github.com/jupyterhub/jupyterhub/pull/3314) ([@timgates42](https://github.com/timgates42))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2020-12-11&to=2021-04-19&type=c))

[@00Kai0](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3A00Kai0+updated%3A2020-12-11..2021-04-19&type=Issues) | [@8rV1n](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3A8rV1n+updated%3A2020-12-11..2021-04-19&type=Issues) | [@akhilputhiry](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aakhilputhiry+updated%3A2020-12-11..2021-04-19&type=Issues) | [@alexal](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aalexal+updated%3A2020-12-11..2021-04-19&type=Issues) | [@analytically](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aanalytically+updated%3A2020-12-11..2021-04-19&type=Issues) | [@andreamazzoni](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aandreamazzoni+updated%3A2020-12-11..2021-04-19&type=Issues) | [@andrewisplinghoff](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aandrewisplinghoff+updated%3A2020-12-11..2021-04-19&type=Issues) | [@BertR](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ABertR+updated%3A2020-12-11..2021-04-19&type=Issues) | [@betatim](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abetatim+updated%3A2020-12-11..2021-04-19&type=Issues) | [@bitnik](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abitnik+updated%3A2020-12-11..2021-04-19&type=Issues) | [@bollwyvl](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abollwyvl+updated%3A2020-12-11..2021-04-19&type=Issues) | [@carluri](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acarluri+updated%3A2020-12-11..2021-04-19&type=Issues) | [@Carreau](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ACarreau+updated%3A2020-12-11..2021-04-19&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2020-12-11..2021-04-19&type=Issues) | [@davidedelvento](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adavidedelvento+updated%3A2020-12-11..2021-04-19&type=Issues) | [@dhirschfeld](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adhirschfeld+updated%3A2020-12-11..2021-04-19&type=Issues) | [@dmpe](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Admpe+updated%3A2020-12-11..2021-04-19&type=Issues) | [@dsblank](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adsblank+updated%3A2020-12-11..2021-04-19&type=Issues) | [@dtaniwaki](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adtaniwaki+updated%3A2020-12-11..2021-04-19&type=Issues) | [@echarles](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aecharles+updated%3A2020-12-11..2021-04-19&type=Issues) | [@elgalu](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aelgalu+updated%3A2020-12-11..2021-04-19&type=Issues) | [@eran-pinhas](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aeran-pinhas+updated%3A2020-12-11..2021-04-19&type=Issues) | [@gaebor](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Agaebor+updated%3A2020-12-11..2021-04-19&type=Issues) | [@GeorgianaElena](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AGeorgianaElena+updated%3A2020-12-11..2021-04-19&type=Issues) | [@gsemet](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Agsemet+updated%3A2020-12-11..2021-04-19&type=Issues) | [@gweis](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Agweis+updated%3A2020-12-11..2021-04-19&type=Issues) | [@hynek2001](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ahynek2001+updated%3A2020-12-11..2021-04-19&type=Issues) | [@ianabc](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aianabc+updated%3A2020-12-11..2021-04-19&type=Issues) | [@ibre5041](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aibre5041+updated%3A2020-12-11..2021-04-19&type=Issues) | [@IvanaH8](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AIvanaH8+updated%3A2020-12-11..2021-04-19&type=Issues) | [@jhegedus42](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajhegedus42+updated%3A2020-12-11..2021-04-19&type=Issues) | [@jhermann](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajhermann+updated%3A2020-12-11..2021-04-19&type=Issues) | [@jiajunjie](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajiajunjie+updated%3A2020-12-11..2021-04-19&type=Issues) | [@jtlz2](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajtlz2+updated%3A2020-12-11..2021-04-19&type=Issues) | [@kafonek](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akafonek+updated%3A2020-12-11..2021-04-19&type=Issues) | [@katsar0v](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akatsar0v+updated%3A2020-12-11..2021-04-19&type=Issues) | [@kinow](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akinow+updated%3A2020-12-11..2021-04-19&type=Issues) | [@krinsman](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akrinsman+updated%3A2020-12-11..2021-04-19&type=Issues) | [@laurensdv](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Alaurensdv+updated%3A2020-12-11..2021-04-19&type=Issues) | [@lits789](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Alits789+updated%3A2020-12-11..2021-04-19&type=Issues) | [@m-alekseev](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Am-alekseev+updated%3A2020-12-11..2021-04-19&type=Issues) | [@mabbasi90](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amabbasi90+updated%3A2020-12-11..2021-04-19&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2020-12-11..2021-04-19&type=Issues) | [@manniche](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanniche+updated%3A2020-12-11..2021-04-19&type=Issues) | [@maxshowarth](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amaxshowarth+updated%3A2020-12-11..2021-04-19&type=Issues) | [@mdivk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amdivk+updated%3A2020-12-11..2021-04-19&type=Issues) | [@meeseeksmachine](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ameeseeksmachine+updated%3A2020-12-11..2021-04-19&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2020-12-11..2021-04-19&type=Issues) | [@mogthesprog](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amogthesprog+updated%3A2020-12-11..2021-04-19&type=Issues) | [@mriedem](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amriedem+updated%3A2020-12-11..2021-04-19&type=Issues) | [@nsshah1288](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ansshah1288+updated%3A2020-12-11..2021-04-19&type=Issues) | [@olifre](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aolifre+updated%3A2020-12-11..2021-04-19&type=Issues) | [@PandaWhoCodes](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3APandaWhoCodes+updated%3A2020-12-11..2021-04-19&type=Issues) | [@pawsaw](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apawsaw+updated%3A2020-12-11..2021-04-19&type=Issues) | [@phozzy](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aphozzy+updated%3A2020-12-11..2021-04-19&type=Issues) | [@playermanny2](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aplayermanny2+updated%3A2020-12-11..2021-04-19&type=Issues) | [@rabsr](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arabsr+updated%3A2020-12-11..2021-04-19&type=Issues) | [@randy3k](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arandy3k+updated%3A2020-12-11..2021-04-19&type=Issues) | [@rawrgulmuffins](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arawrgulmuffins+updated%3A2020-12-11..2021-04-19&type=Issues) | [@rcthomas](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arcthomas+updated%3A2020-12-11..2021-04-19&type=Issues) | [@rebeca-maia](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arebeca-maia+updated%3A2020-12-11..2021-04-19&type=Issues) | [@rebenkoy](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arebenkoy+updated%3A2020-12-11..2021-04-19&type=Issues) | [@rkdarst](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arkdarst+updated%3A2020-12-11..2021-04-19&type=Issues) | [@robnagler](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arobnagler+updated%3A2020-12-11..2021-04-19&type=Issues) | [@ronaldpetty](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aronaldpetty+updated%3A2020-12-11..2021-04-19&type=Issues) | [@ryanlovett](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aryanlovett+updated%3A2020-12-11..2021-04-19&type=Issues) | [@ryogesh](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aryogesh+updated%3A2020-12-11..2021-04-19&type=Issues) | [@sbailey-auro](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asbailey-auro+updated%3A2020-12-11..2021-04-19&type=Issues) | [@sigurdurb](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asigurdurb+updated%3A2020-12-11..2021-04-19&type=Issues) | [@SivaAccionLabs](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ASivaAccionLabs+updated%3A2020-12-11..2021-04-19&type=Issues) | [@sougou](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asougou+updated%3A2020-12-11..2021-04-19&type=Issues) | [@stv0g](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Astv0g+updated%3A2020-12-11..2021-04-19&type=Issues) | [@sudi007](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asudi007+updated%3A2020-12-11..2021-04-19&type=Issues) | [@support](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asupport+updated%3A2020-12-11..2021-04-19&type=Issues) | [@tathagata](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atathagata+updated%3A2020-12-11..2021-04-19&type=Issues) | [@timgates42](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atimgates42+updated%3A2020-12-11..2021-04-19&type=Issues) | [@trallard](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atrallard+updated%3A2020-12-11..2021-04-19&type=Issues) | [@vlizanae](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Avlizanae+updated%3A2020-12-11..2021-04-19&type=Issues) | [@welcome](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awelcome+updated%3A2020-12-11..2021-04-19&type=Issues) | [@whitespaceninja](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awhitespaceninja+updated%3A2020-12-11..2021-04-19&type=Issues) | [@whlteXbread](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AwhlteXbread+updated%3A2020-12-11..2021-04-19&type=Issues) | [@willingc](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awillingc+updated%3A2020-12-11..2021-04-19&type=Issues) | [@yuvipanda](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2020-12-11..2021-04-19&type=Issues) | [@Zsailer](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AZsailer+updated%3A2020-12-11..2021-04-19&type=Issues)

## 1.3

JupyterHub 1.3 is a small feature release. Highlights include:

- Require Python >=3.6 (jupyterhub 1.2 is the last release to support 3.5)
- Add a `?state=` filter for getting user list, allowing much quicker responses
  when retrieving a small fraction of users.
  `state` can be `active`, `inactive`, or `ready`.
- prometheus metrics now include a `jupyterhub_` prefix,
  so deployments may need to update their grafana charts to match.
- page templates can now be [async](https://jinja.palletsprojects.com/en/2.11.x/api/#async-support)!

### [1.3.0]

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/1.2.1...1.3.0))

#### Enhancements made

- allow services to call /api/user to identify themselves [#3293](https://github.com/jupyterhub/jupyterhub/pull/3293) ([@minrk](https://github.com/minrk))
- Add optional user agreement to login screen [#3264](https://github.com/jupyterhub/jupyterhub/pull/3264) ([@tlvu](https://github.com/tlvu))
- [Metrics] Add prefix to prometheus metrics to group all jupyterhub metrics [#3243](https://github.com/jupyterhub/jupyterhub/pull/3243) ([@agp8x](https://github.com/agp8x))
- Allow options_from_form to be configurable [#3225](https://github.com/jupyterhub/jupyterhub/pull/3225) ([@cbanek](https://github.com/cbanek))
- add ?state= filter for GET /users [#3177](https://github.com/jupyterhub/jupyterhub/pull/3177) ([@minrk](https://github.com/minrk))
- Enable async support in jinja2 templates [#3176](https://github.com/jupyterhub/jupyterhub/pull/3176) ([@yuvipanda](https://github.com/yuvipanda))

#### Bugs fixed

- fix increasing pagination limits [#3294](https://github.com/jupyterhub/jupyterhub/pull/3294) ([@minrk](https://github.com/minrk))
- fix and test TOTAL_USERS count [#3289](https://github.com/jupyterhub/jupyterhub/pull/3289) ([@minrk](https://github.com/minrk))
- Fix asyncio deprecation asyncio.Task.all_tasks [#3298](https://github.com/jupyterhub/jupyterhub/pull/3298) ([@coffeebenzene](https://github.com/coffeebenzene))

#### Maintenance and upkeep improvements

- bump oldest-required prometheus-client [#3292](https://github.com/jupyterhub/jupyterhub/pull/3292) ([@minrk](https://github.com/minrk))
- bump black pre-commit hook to 20.8 [#3287](https://github.com/jupyterhub/jupyterhub/pull/3287) ([@minrk](https://github.com/minrk))
- Test internal_ssl separately [#3266](https://github.com/jupyterhub/jupyterhub/pull/3266) ([@0mar](https://github.com/0mar))
- wait for pending spawns in spawn_form_admin_access [#3253](https://github.com/jupyterhub/jupyterhub/pull/3253) ([@minrk](https://github.com/minrk))
- Assume py36 and remove @gen.coroutine etc. [#3242](https://github.com/jupyterhub/jupyterhub/pull/3242) ([@consideRatio](https://github.com/consideRatio))

#### Documentation improvements

- Fix curl in jupyter announcements [#3286](https://github.com/jupyterhub/jupyterhub/pull/3286) ([@Sangarshanan](https://github.com/Sangarshanan))
- CONTRIBUTING: Fix contributor guide URL [#3281](https://github.com/jupyterhub/jupyterhub/pull/3281) ([@olifre](https://github.com/olifre))
- Update services.md [#3267](https://github.com/jupyterhub/jupyterhub/pull/3267) ([@slemonide](https://github.com/slemonide))
- [Docs] Fix https reverse proxy redirect issues [#3244](https://github.com/jupyterhub/jupyterhub/pull/3244) ([@mhwasil](https://github.com/mhwasil))
- Fixed idle-culler references. [#3300](https://github.com/jupyterhub/jupyterhub/pull/3300) ([@mxjeff](https://github.com/mxjeff))
- Remove the extra parenthesis in service.md [#3303](https://github.com/jupyterhub/jupyterhub/pull/3303) ([@Sangarshanan](https://github.com/Sangarshanan))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2020-10-30&to=2020-12-11&type=c))

[@0mar](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3A0mar+updated%3A2020-10-30..2020-12-11&type=Issues) | [@agp8x](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aagp8x+updated%3A2020-10-30..2020-12-11&type=Issues) | [@alexweav](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aalexweav+updated%3A2020-10-30..2020-12-11&type=Issues) | [@belfhi](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abelfhi+updated%3A2020-10-30..2020-12-11&type=Issues) | [@betatim](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abetatim+updated%3A2020-10-30..2020-12-11&type=Issues) | [@cbanek](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acbanek+updated%3A2020-10-30..2020-12-11&type=Issues) | [@cmd-ntrf](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acmd-ntrf+updated%3A2020-10-30..2020-12-11&type=Issues) | [@coffeebenzene](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acoffeebenzene+updated%3A2020-10-30..2020-12-11&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2020-10-30..2020-12-11&type=Issues) | [@danlester](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adanlester+updated%3A2020-10-30..2020-12-11&type=Issues) | [@fcollonval](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Afcollonval+updated%3A2020-10-30..2020-12-11&type=Issues) | [@GeorgianaElena](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AGeorgianaElena+updated%3A2020-10-30..2020-12-11&type=Issues) | [@ianabc](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aianabc+updated%3A2020-10-30..2020-12-11&type=Issues) | [@IvanaH8](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AIvanaH8+updated%3A2020-10-30..2020-12-11&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2020-10-30..2020-12-11&type=Issues) | [@meeseeksmachine](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ameeseeksmachine+updated%3A2020-10-30..2020-12-11&type=Issues) | [@mhwasil](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amhwasil+updated%3A2020-10-30..2020-12-11&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2020-10-30..2020-12-11&type=Issues) | [@mriedem](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amriedem+updated%3A2020-10-30..2020-12-11&type=Issues) | [@mxjeff](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amxjeff+updated%3A2020-10-30..2020-12-11&type=Issues) | [@olifre](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aolifre+updated%3A2020-10-30..2020-12-11&type=Issues) | [@rcthomas](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arcthomas+updated%3A2020-10-30..2020-12-11&type=Issues) | [@rgbkrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Argbkrk+updated%3A2020-10-30..2020-12-11&type=Issues) | [@rkdarst](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arkdarst+updated%3A2020-10-30..2020-12-11&type=Issues) | [@Sangarshanan](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ASangarshanan+updated%3A2020-10-30..2020-12-11&type=Issues) | [@slemonide](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aslemonide+updated%3A2020-10-30..2020-12-11&type=Issues) | [@support](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asupport+updated%3A2020-10-30..2020-12-11&type=Issues) | [@tlvu](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atlvu+updated%3A2020-10-30..2020-12-11&type=Issues) | [@welcome](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awelcome+updated%3A2020-10-30..2020-12-11&type=Issues) | [@yuvipanda](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2020-10-30..2020-12-11&type=Issues)

## 1.2

### [1.2.2] 2020-11-27

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/1.2.1...41f291c0c973223c33a6aa1fa86d5d57f297be78))

#### Enhancements made

- Standardize "Sign in" capitalization on the login page [#3252](https://github.com/jupyterhub/jupyterhub/pull/3252) ([@cmd-ntrf](https://github.com/cmd-ntrf))

#### Bugs fixed

- Fix RootHandler when default_url is a callable [#3265](https://github.com/jupyterhub/jupyterhub/pull/3265) ([@danlester](https://github.com/danlester))
- Only preserve params when ?next= is unspecified [#3261](https://github.com/jupyterhub/jupyterhub/pull/3261) ([@minrk](https://github.com/minrk))
- \[Windows\] Improve robustness when detecting and closing existing proxy processes [#3237](https://github.com/jupyterhub/jupyterhub/pull/3237) ([@alexweav](https://github.com/alexweav))

#### Maintenance and upkeep improvements

- Environment marker on pamela [#3255](https://github.com/jupyterhub/jupyterhub/pull/3255) ([@fcollonval](https://github.com/fcollonval))
- remove push-branch conditions for CI [#3250](https://github.com/jupyterhub/jupyterhub/pull/3250) ([@minrk](https://github.com/minrk))
- Migrate from travis to GitHub actions [#3246](https://github.com/jupyterhub/jupyterhub/pull/3246) ([@consideRatio](https://github.com/consideRatio))

#### Documentation improvements

- Update services-basics.md to use jupyterhub_idle_culler [#3257](https://github.com/jupyterhub/jupyterhub/pull/3257) ([@manics](https://github.com/manics))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2020-10-30&to=2020-11-27&type=c))

[@alexweav](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aalexweav+updated%3A2020-10-30..2020-11-27&type=Issues) | [@belfhi](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abelfhi+updated%3A2020-10-30..2020-11-27&type=Issues) | [@betatim](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abetatim+updated%3A2020-10-30..2020-11-27&type=Issues) | [@cmd-ntrf](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acmd-ntrf+updated%3A2020-10-30..2020-11-27&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2020-10-30..2020-11-27&type=Issues) | [@danlester](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adanlester+updated%3A2020-10-30..2020-11-27&type=Issues) | [@fcollonval](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Afcollonval+updated%3A2020-10-30..2020-11-27&type=Issues) | [@GeorgianaElena](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AGeorgianaElena+updated%3A2020-10-30..2020-11-27&type=Issues) | [@ianabc](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aianabc+updated%3A2020-10-30..2020-11-27&type=Issues) | [@IvanaH8](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AIvanaH8+updated%3A2020-10-30..2020-11-27&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2020-10-30..2020-11-27&type=Issues) | [@meeseeksmachine](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ameeseeksmachine+updated%3A2020-10-30..2020-11-27&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2020-10-30..2020-11-27&type=Issues) | [@mriedem](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amriedem+updated%3A2020-10-30..2020-11-27&type=Issues) | [@olifre](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aolifre+updated%3A2020-10-30..2020-11-27&type=Issues) | [@rcthomas](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arcthomas+updated%3A2020-10-30..2020-11-27&type=Issues) | [@rgbkrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Argbkrk+updated%3A2020-10-30..2020-11-27&type=Issues) | [@rkdarst](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arkdarst+updated%3A2020-10-30..2020-11-27&type=Issues) | [@slemonide](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aslemonide+updated%3A2020-10-30..2020-11-27&type=Issues) | [@support](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asupport+updated%3A2020-10-30..2020-11-27&type=Issues) | [@welcome](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awelcome+updated%3A2020-10-30..2020-11-27&type=Issues) | [@yuvipanda](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2020-10-30..2020-11-27&type=Issues)

### [1.2.1] 2020-10-30

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/1.2.0...1.2.1))

#### Bugs fixed

- JupyterHub services' oauth_no_confirm configuration regression in 1.2.0 [#3234](https://github.com/jupyterhub/jupyterhub/pull/3234) ([@bitnik](https://github.com/bitnik))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2020-10-29&to=2020-10-30&type=c))

[@bitnik](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abitnik+updated%3A2020-10-29..2020-10-30&type=Issues)

### [1.2.0] 2020-10-29

JupyterHub 1.2 is an incremental release with lots of small improvements.
It is unlikely that users will have to change much to upgrade,
but lots of new things are possible and/or better!

There are no database schema changes requiring migration from 1.1 to 1.2.

Highlights:

- Deprecate black/whitelist configuration fields in favor of more inclusive blocked/allowed language. For example: `c.Authenticator.allowed_users = {'user', ...}`
- More configuration of page templates and service display
- Pagination of the admin page improving performance with large numbers of users
- Improved control of user redirect
- Support for [jupyter-server](https://jupyter-server.readthedocs.io/en/latest/)-based single-user servers, such as [Voilà](https://voila-gallery.org) and latest JupyterLab.
- Lots more improvements to documentation, HTML pages, and customizations

([full changelog](https://github.com/jupyterhub/jupyterhub/compare/1.1.0...1.2.0))

#### Enhancements made

- make pagination configurable [#3229](https://github.com/jupyterhub/jupyterhub/pull/3229) ([@minrk](https://github.com/minrk))
- Make api_request to CHP's REST API more reliable [#3223](https://github.com/jupyterhub/jupyterhub/pull/3223) ([@consideRatio](https://github.com/consideRatio))
- Control service display [#3160](https://github.com/jupyterhub/jupyterhub/pull/3160) ([@rcthomas](https://github.com/rcthomas))
- Add a footer block + wrap the admin footer in this block [#3136](https://github.com/jupyterhub/jupyterhub/pull/3136) ([@pabepadu](https://github.com/pabepadu))
- Allow JupyterHub.default_url to be a callable [#3133](https://github.com/jupyterhub/jupyterhub/pull/3133) ([@danlester](https://github.com/danlester))
- Allow head requests for the health endpoint [#3131](https://github.com/jupyterhub/jupyterhub/pull/3131) ([@rkevin-arch](https://github.com/rkevin-arch))
- Hide hamburger button menu in mobile/responsive mode and fix other minor issues [#3103](https://github.com/jupyterhub/jupyterhub/pull/3103) ([@kinow](https://github.com/kinow))
- build jupyterhub/jupyterhub-demo image on docker hub [#3083](https://github.com/jupyterhub/jupyterhub/pull/3083) ([@minrk](https://github.com/minrk))
- Add JupyterHub Demo docker image [#3059](https://github.com/jupyterhub/jupyterhub/pull/3059) ([@GeorgianaElena](https://github.com/GeorgianaElena))
- Warn if both bind_url and ip/port/base_url are set [#3057](https://github.com/jupyterhub/jupyterhub/pull/3057) ([@GeorgianaElena](https://github.com/GeorgianaElena))
- UI Feedback on Submit [#3028](https://github.com/jupyterhub/jupyterhub/pull/3028) ([@possiblyMikeB](https://github.com/possiblyMikeB))
- Support kubespawner running on a IPv6 only cluster [#3020](https://github.com/jupyterhub/jupyterhub/pull/3020) ([@stv0g](https://github.com/stv0g))
- Spawn with options passed in query arguments to /spawn [#3013](https://github.com/jupyterhub/jupyterhub/pull/3013) ([@twalcari](https://github.com/twalcari))
- SpawnHandler POST with user form options displays the spawn-pending page [#2978](https://github.com/jupyterhub/jupyterhub/pull/2978) ([@danlester](https://github.com/danlester))
- Start named servers by pressing the Enter key [#2960](https://github.com/jupyterhub/jupyterhub/pull/2960) ([@jtpio](https://github.com/jtpio))
- Keep the URL fragments after spawning an application [#2952](https://github.com/jupyterhub/jupyterhub/pull/2952) ([@kinow](https://github.com/kinow))
- Allow implicit spawn via javascript redirect [#2941](https://github.com/jupyterhub/jupyterhub/pull/2941) ([@minrk](https://github.com/minrk))
- make init_spawners check O(running servers) not O(total users) [#2936](https://github.com/jupyterhub/jupyterhub/pull/2936) ([@minrk](https://github.com/minrk))
- Add favicon to the base page template [#2930](https://github.com/jupyterhub/jupyterhub/pull/2930) ([@JohnPaton](https://github.com/JohnPaton))
- Adding pagination in the admin panel [#2929](https://github.com/jupyterhub/jupyterhub/pull/2929) ([@cbjuan](https://github.com/cbjuan))
- Generate prometheus metrics docs [#2891](https://github.com/jupyterhub/jupyterhub/pull/2891) ([@rajat404](https://github.com/rajat404))
- Add support for Jupyter Server [#2601](https://github.com/jupyterhub/jupyterhub/pull/2601) ([@yuvipanda](https://github.com/yuvipanda))

#### Bugs fixed

- Fix #2284 must be sent from authorization page [#3219](https://github.com/jupyterhub/jupyterhub/pull/3219) ([@elgalu](https://github.com/elgalu))
- avoid specifying default_value=None in Command traits [#3208](https://github.com/jupyterhub/jupyterhub/pull/3208) ([@minrk](https://github.com/minrk))
- Prevent OverflowErrors in exponential_backoff() [#3204](https://github.com/jupyterhub/jupyterhub/pull/3204) ([@kreuzert](https://github.com/kreuzert))
- update prometheus metrics for server spawn when it fails with exception [#3150](https://github.com/jupyterhub/jupyterhub/pull/3150) ([@yhal-nesi](https://github.com/yhal-nesi))
- jupyterhub/utils: Load system default CA certificates in make_ssl_context [#3140](https://github.com/jupyterhub/jupyterhub/pull/3140) ([@chancez](https://github.com/chancez))
- admin page sorts on spawner last_activity instead of user last_activity [#3137](https://github.com/jupyterhub/jupyterhub/pull/3137) ([@lydian](https://github.com/lydian))
- Fix the services dropdown on the admin page [#3132](https://github.com/jupyterhub/jupyterhub/pull/3132) ([@pabepadu](https://github.com/pabepadu))
- Don't log a warning when slow_spawn_timeout is disabled [#3127](https://github.com/jupyterhub/jupyterhub/pull/3127) ([@mriedem](https://github.com/mriedem))
- app.py: Work around incompatibility between Tornado 6 and asyncio proactor event loop in python 3.8 on Windows [#3123](https://github.com/jupyterhub/jupyterhub/pull/3123) ([@alexweav](https://github.com/alexweav))
- jupyterhub/user: clear spawner state after post_stop_hook [#3121](https://github.com/jupyterhub/jupyterhub/pull/3121) ([@rkdarst](https://github.com/rkdarst))
- fix for stopping named server deleting default server and tests [#3109](https://github.com/jupyterhub/jupyterhub/pull/3109) ([@kxiao-fn](https://github.com/kxiao-fn))
- Hide hamburger button menu in mobile/responsive mode and fix other minor issues [#3103](https://github.com/jupyterhub/jupyterhub/pull/3103) ([@kinow](https://github.com/kinow))
- Rename Authenticator.white/blacklist to allowed/blocked [#3090](https://github.com/jupyterhub/jupyterhub/pull/3090) ([@minrk](https://github.com/minrk))
- Include the query string parameters when redirecting to a new URL [#3089](https://github.com/jupyterhub/jupyterhub/pull/3089) ([@kinow](https://github.com/kinow))
- Make `delete_invalid_users` configurable [#3087](https://github.com/jupyterhub/jupyterhub/pull/3087) ([@fcollonval](https://github.com/fcollonval))
- Ensure client dependencies build before wheel [#3082](https://github.com/jupyterhub/jupyterhub/pull/3082) ([@diurnalist](https://github.com/diurnalist))
- make Spawner.environment config highest priority [#3081](https://github.com/jupyterhub/jupyterhub/pull/3081) ([@minrk](https://github.com/minrk))
- Changing start my server button link to spawn url once server is stopped [#3042](https://github.com/jupyterhub/jupyterhub/pull/3042) ([@rabsr](https://github.com/rabsr))
- Fix CSS on admin page version listing [#3035](https://github.com/jupyterhub/jupyterhub/pull/3035) ([@vilhelmen](https://github.com/vilhelmen))
- Fix user_row endblock in admin template [#3015](https://github.com/jupyterhub/jupyterhub/pull/3015) ([@jtpio](https://github.com/jtpio))
- Fix --generate-config bug when specifying a filename [#2907](https://github.com/jupyterhub/jupyterhub/pull/2907) ([@consideRatio](https://github.com/consideRatio))
- Handle the protocol when ssl is enabled and log the right URL [#2773](https://github.com/jupyterhub/jupyterhub/pull/2773) ([@kinow](https://github.com/kinow))

#### Maintenance and upkeep improvements

- Update travis-ci badge in README.md [#3232](https://github.com/jupyterhub/jupyterhub/pull/3232) ([@consideRatio](https://github.com/consideRatio))
- stop building docs on circleci [#3209](https://github.com/jupyterhub/jupyterhub/pull/3209) ([@minrk](https://github.com/minrk))
- Upgraded Jquery dep [#3174](https://github.com/jupyterhub/jupyterhub/pull/3174) ([@AngelOnFira](https://github.com/AngelOnFira))
- Don't allow 'python:3.8 + master dependencies' to fail [#3157](https://github.com/jupyterhub/jupyterhub/pull/3157) ([@manics](https://github.com/manics))
- Update Dockerfile to ubuntu:focal (Python 3.8) [#3156](https://github.com/jupyterhub/jupyterhub/pull/3156) ([@manics](https://github.com/manics))
- Simplify code of the health check handler [#3149](https://github.com/jupyterhub/jupyterhub/pull/3149) ([@betatim](https://github.com/betatim))
- Get error description from error key vs error_description key [#3147](https://github.com/jupyterhub/jupyterhub/pull/3147) ([@jgwerner](https://github.com/jgwerner))
- Implement singleuser with mixins [#3128](https://github.com/jupyterhub/jupyterhub/pull/3128) ([@minrk](https://github.com/minrk))
- only build tagged versions on docker tags [#3118](https://github.com/jupyterhub/jupyterhub/pull/3118) ([@minrk](https://github.com/minrk))
- Log slow_stop_timeout when hit like slow_spawn_timeout [#3111](https://github.com/jupyterhub/jupyterhub/pull/3111) ([@mriedem](https://github.com/mriedem))
- loosen jupyter-telemetry pin [#3102](https://github.com/jupyterhub/jupyterhub/pull/3102) ([@minrk](https://github.com/minrk))
- Remove old context-less print statement [#3100](https://github.com/jupyterhub/jupyterhub/pull/3100) ([@mriedem](https://github.com/mriedem))
- Allow `python:3.8 + master dependencies` to fail [#3079](https://github.com/jupyterhub/jupyterhub/pull/3079) ([@manics](https://github.com/manics))
- Test with some master dependencies. [#3076](https://github.com/jupyterhub/jupyterhub/pull/3076) ([@Carreau](https://github.com/Carreau))
- synchronize implementation of expiring values [#3072](https://github.com/jupyterhub/jupyterhub/pull/3072) ([@minrk](https://github.com/minrk))
- More consistent behavior for UserDict.get and `key in UserDict` [#3071](https://github.com/jupyterhub/jupyterhub/pull/3071) ([@minrk](https://github.com/minrk))
- pin jupyter_telemetry dependency [#3067](https://github.com/jupyterhub/jupyterhub/pull/3067) ([@Zsailer](https://github.com/Zsailer))
- Use the issue templates from the central repo [#3056](https://github.com/jupyterhub/jupyterhub/pull/3056) ([@GeorgianaElena](https://github.com/GeorgianaElena))
- Update links to the black GitHub repository [#3054](https://github.com/jupyterhub/jupyterhub/pull/3054) ([@jtpio](https://github.com/jtpio))
- Log successful /health requests as debug level [#3047](https://github.com/jupyterhub/jupyterhub/pull/3047) ([@consideRatio](https://github.com/consideRatio))
- Fix broken test due to BeautifulSoup 4.9.0 behavior change [#3025](https://github.com/jupyterhub/jupyterhub/pull/3025) ([@twalcari](https://github.com/twalcari))
- Remove unused imports [#3019](https://github.com/jupyterhub/jupyterhub/pull/3019) ([@stv0g](https://github.com/stv0g))
- Use pip instead of conda for building the docs on RTD [#3010](https://github.com/jupyterhub/jupyterhub/pull/3010) ([@GeorgianaElena](https://github.com/GeorgianaElena))
- Avoid redundant logging of jupyterhub version mismatches [#2971](https://github.com/jupyterhub/jupyterhub/pull/2971) ([@mriedem](https://github.com/mriedem))
- Add .vscode to gitignore [#2959](https://github.com/jupyterhub/jupyterhub/pull/2959) ([@jtpio](https://github.com/jtpio))
- preserve auth type when logging obfuscated auth header [#2953](https://github.com/jupyterhub/jupyterhub/pull/2953) ([@minrk](https://github.com/minrk))
- make spawner:server relationship explicitly one to one [#2944](https://github.com/jupyterhub/jupyterhub/pull/2944) ([@minrk](https://github.com/minrk))
- Add what we need with some margin to Dockerfile's build stage [#2905](https://github.com/jupyterhub/jupyterhub/pull/2905) ([@consideRatio](https://github.com/consideRatio))
- bump reorder-imports hook [#2899](https://github.com/jupyterhub/jupyterhub/pull/2899) ([@minrk](https://github.com/minrk))

#### Documentation improvements

- Fix typo in documentation [#3226](https://github.com/jupyterhub/jupyterhub/pull/3226) ([@xlotlu](https://github.com/xlotlu))
- [docs] Remove duplicate line in changelog for 1.1.0 [#3207](https://github.com/jupyterhub/jupyterhub/pull/3207) ([@kinow](https://github.com/kinow))
- changelog for 1.2.0b1 [#3192](https://github.com/jupyterhub/jupyterhub/pull/3192) ([@consideRatio](https://github.com/consideRatio))
- Add SELinux configuration for nginx [#3185](https://github.com/jupyterhub/jupyterhub/pull/3185) ([@rainwoodman](https://github.com/rainwoodman))
- Mention the PAM pitfall on fedora. [#3184](https://github.com/jupyterhub/jupyterhub/pull/3184) ([@rainwoodman](https://github.com/rainwoodman))
- Added extra documentation for endpoint /users/{name}/servers/{server_name}. [#3159](https://github.com/jupyterhub/jupyterhub/pull/3159) ([@synchronizing](https://github.com/synchronizing))
- docs: please docs linter (move_cert docstring) [#3151](https://github.com/jupyterhub/jupyterhub/pull/3151) ([@consideRatio](https://github.com/consideRatio))
- Needed NoEsacpe (NE) option for apache [#3143](https://github.com/jupyterhub/jupyterhub/pull/3143) ([@basvandervlies](https://github.com/basvandervlies))
- Document external service api_tokens better [#3142](https://github.com/jupyterhub/jupyterhub/pull/3142) ([@snickell](https://github.com/snickell))
- Remove idle culler example [#3114](https://github.com/jupyterhub/jupyterhub/pull/3114) ([@yuvipanda](https://github.com/yuvipanda))
- docs: unsqueeze logo, remove unused CSS and templates [#3107](https://github.com/jupyterhub/jupyterhub/pull/3107) ([@consideRatio](https://github.com/consideRatio))
- Update version in docs/rest-api.yaml [#3104](https://github.com/jupyterhub/jupyterhub/pull/3104) ([@cmd-ntrf](https://github.com/cmd-ntrf))
- Replace zonca/remotespawner with NERSC/sshspawner [#3086](https://github.com/jupyterhub/jupyterhub/pull/3086) ([@manics](https://github.com/manics))
- Remove already done named servers from roadmap [#3084](https://github.com/jupyterhub/jupyterhub/pull/3084) ([@elgalu](https://github.com/elgalu))
- proxy settings might cause authentication errors [#3078](https://github.com/jupyterhub/jupyterhub/pull/3078) ([@gatoniel](https://github.com/gatoniel))
- Add Configuration Reference section to docs [#3077](https://github.com/jupyterhub/jupyterhub/pull/3077) ([@kinow](https://github.com/kinow))
- document upgrading from api_tokens to services config [#3055](https://github.com/jupyterhub/jupyterhub/pull/3055) ([@minrk](https://github.com/minrk))
- [Docs] Disable proxy_buffering when using nginx reverse proxy [#3048](https://github.com/jupyterhub/jupyterhub/pull/3048) ([@mhwasil](https://github.com/mhwasil))
- docs: add proxy_http_version 1.1 [#3046](https://github.com/jupyterhub/jupyterhub/pull/3046) ([@ceocoder](https://github.com/ceocoder))
- #1018 PAM added in prerequisites [#3040](https://github.com/jupyterhub/jupyterhub/pull/3040) ([@romainx](https://github.com/romainx))
- Fix use of auxiliary verb on index.rst [#3022](https://github.com/jupyterhub/jupyterhub/pull/3022) ([@joshmeek](https://github.com/joshmeek))
- Fix docs CI test failure: duplicate object description [#3021](https://github.com/jupyterhub/jupyterhub/pull/3021) ([@rkdarst](https://github.com/rkdarst))
- Update issue templates [#3001](https://github.com/jupyterhub/jupyterhub/pull/3001) ([@GeorgianaElena](https://github.com/GeorgianaElena))
- fix wrong name on firewall [#2997](https://github.com/jupyterhub/jupyterhub/pull/2997) ([@thuvh](https://github.com/thuvh))
- updating docs theme [#2995](https://github.com/jupyterhub/jupyterhub/pull/2995) ([@choldgraf](https://github.com/choldgraf))
- Update contributor docs [#2972](https://github.com/jupyterhub/jupyterhub/pull/2972) ([@mriedem](https://github.com/mriedem))
- Server.user_options rest-api documented [#2966](https://github.com/jupyterhub/jupyterhub/pull/2966) ([@mriedem](https://github.com/mriedem))
- Pin sphinx theme [#2956](https://github.com/jupyterhub/jupyterhub/pull/2956) ([@manics](https://github.com/manics))
- [doc] Fix couple typos in the documentation [#2951](https://github.com/jupyterhub/jupyterhub/pull/2951) ([@kinow](https://github.com/kinow))
- Docs: Fixed grammar on landing page [#2950](https://github.com/jupyterhub/jupyterhub/pull/2950) ([@alexdriedger](https://github.com/alexdriedger))
- add general faq [#2946](https://github.com/jupyterhub/jupyterhub/pull/2946) ([@minrk](https://github.com/minrk))
- docs: use metachannel for faster environment solve [#2943](https://github.com/jupyterhub/jupyterhub/pull/2943) ([@minrk](https://github.com/minrk))
- update docs environments [#2942](https://github.com/jupyterhub/jupyterhub/pull/2942) ([@minrk](https://github.com/minrk))
- [doc] Add more docs about Cookies used for authentication in JupyterHub [#2940](https://github.com/jupyterhub/jupyterhub/pull/2940) ([@kinow](https://github.com/kinow))
- [doc] Use fixed commit plus line number in github link [#2939](https://github.com/jupyterhub/jupyterhub/pull/2939) ([@kinow](https://github.com/kinow))
- [doc] Fix link to SSL encryption from troubleshooting page [#2938](https://github.com/jupyterhub/jupyterhub/pull/2938) ([@kinow](https://github.com/kinow))
- rest api: fix schema for remove parameter in rest api [#2917](https://github.com/jupyterhub/jupyterhub/pull/2917) ([@minrk](https://github.com/minrk))
- Add troubleshooting topics [#2914](https://github.com/jupyterhub/jupyterhub/pull/2914) ([@jgwerner](https://github.com/jgwerner))
- Several fixes to the doc [#2904](https://github.com/jupyterhub/jupyterhub/pull/2904) ([@reneluria](https://github.com/reneluria))
- fix: 'Non-ASCII character '\xc3' [#2901](https://github.com/jupyterhub/jupyterhub/pull/2901) ([@jgwerner](https://github.com/jgwerner))
- Generate prometheus metrics docs [#2891](https://github.com/jupyterhub/jupyterhub/pull/2891) ([@rajat404](https://github.com/rajat404))

#### Contributors to this release

([GitHub contributors page for this release](https://github.com/jupyterhub/jupyterhub/graphs/contributors?from=2020-01-17&to=2020-10-29&type=c))

[@0nebody](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3A0nebody+updated%3A2020-01-17..2020-10-29&type=Issues) | [@1kastner](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3A1kastner+updated%3A2020-01-17..2020-10-29&type=Issues) | [@ahkui](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aahkui+updated%3A2020-01-17..2020-10-29&type=Issues) | [@alexdriedger](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aalexdriedger+updated%3A2020-01-17..2020-10-29&type=Issues) | [@alexweav](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aalexweav+updated%3A2020-01-17..2020-10-29&type=Issues) | [@AlJohri](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AAlJohri+updated%3A2020-01-17..2020-10-29&type=Issues) | [@Analect](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AAnalect+updated%3A2020-01-17..2020-10-29&type=Issues) | [@analytically](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aanalytically+updated%3A2020-01-17..2020-10-29&type=Issues) | [@aneagoe](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aaneagoe+updated%3A2020-01-17..2020-10-29&type=Issues) | [@AngelOnFira](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AAngelOnFira+updated%3A2020-01-17..2020-10-29&type=Issues) | [@barrachri](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abarrachri+updated%3A2020-01-17..2020-10-29&type=Issues) | [@basvandervlies](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abasvandervlies+updated%3A2020-01-17..2020-10-29&type=Issues) | [@betatim](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abetatim+updated%3A2020-01-17..2020-10-29&type=Issues) | [@bigbosst](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Abigbosst+updated%3A2020-01-17..2020-10-29&type=Issues) | [@blink1073](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ablink1073+updated%3A2020-01-17..2020-10-29&type=Issues) | [@Cadair](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ACadair+updated%3A2020-01-17..2020-10-29&type=Issues) | [@Carreau](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ACarreau+updated%3A2020-01-17..2020-10-29&type=Issues) | [@cbjuan](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acbjuan+updated%3A2020-01-17..2020-10-29&type=Issues) | [@ceocoder](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aceocoder+updated%3A2020-01-17..2020-10-29&type=Issues) | [@chancez](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Achancez+updated%3A2020-01-17..2020-10-29&type=Issues) | [@choldgraf](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acholdgraf+updated%3A2020-01-17..2020-10-29&type=Issues) | [@Chrisjw42](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AChrisjw42+updated%3A2020-01-17..2020-10-29&type=Issues) | [@cmd-ntrf](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Acmd-ntrf+updated%3A2020-01-17..2020-10-29&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AconsideRatio+updated%3A2020-01-17..2020-10-29&type=Issues) | [@danlester](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adanlester+updated%3A2020-01-17..2020-10-29&type=Issues) | [@diurnalist](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adiurnalist+updated%3A2020-01-17..2020-10-29&type=Issues) | [@Dmitry1987](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ADmitry1987+updated%3A2020-01-17..2020-10-29&type=Issues) | [@dsblank](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adsblank+updated%3A2020-01-17..2020-10-29&type=Issues) | [@dylex](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Adylex+updated%3A2020-01-17..2020-10-29&type=Issues) | [@echarles](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aecharles+updated%3A2020-01-17..2020-10-29&type=Issues) | [@elgalu](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aelgalu+updated%3A2020-01-17..2020-10-29&type=Issues) | [@fcollonval](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Afcollonval+updated%3A2020-01-17..2020-10-29&type=Issues) | [@gatoniel](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Agatoniel+updated%3A2020-01-17..2020-10-29&type=Issues) | [@GeorgianaElena](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AGeorgianaElena+updated%3A2020-01-17..2020-10-29&type=Issues) | [@hnykda](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ahnykda+updated%3A2020-01-17..2020-10-29&type=Issues) | [@itssimon](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aitssimon+updated%3A2020-01-17..2020-10-29&type=Issues) | [@jgwerner](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajgwerner+updated%3A2020-01-17..2020-10-29&type=Issues) | [@JohnPaton](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AJohnPaton+updated%3A2020-01-17..2020-10-29&type=Issues) | [@joshmeek](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajoshmeek+updated%3A2020-01-17..2020-10-29&type=Issues) | [@jtpio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ajtpio+updated%3A2020-01-17..2020-10-29&type=Issues) | [@kinow](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akinow+updated%3A2020-01-17..2020-10-29&type=Issues) | [@kreuzert](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akreuzert+updated%3A2020-01-17..2020-10-29&type=Issues) | [@kxiao-fn](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Akxiao-fn+updated%3A2020-01-17..2020-10-29&type=Issues) | [@lesiano](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Alesiano+updated%3A2020-01-17..2020-10-29&type=Issues) | [@limimiking](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Alimimiking+updated%3A2020-01-17..2020-10-29&type=Issues) | [@lydian](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Alydian+updated%3A2020-01-17..2020-10-29&type=Issues) | [@mabbasi90](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amabbasi90+updated%3A2020-01-17..2020-10-29&type=Issues) | [@maluhoss](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amaluhoss+updated%3A2020-01-17..2020-10-29&type=Issues) | [@manics](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amanics+updated%3A2020-01-17..2020-10-29&type=Issues) | [@matteoipri](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amatteoipri+updated%3A2020-01-17..2020-10-29&type=Issues) | [@mbmilligan](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ambmilligan+updated%3A2020-01-17..2020-10-29&type=Issues) | [@meeseeksmachine](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ameeseeksmachine+updated%3A2020-01-17..2020-10-29&type=Issues) | [@mhwasil](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amhwasil+updated%3A2020-01-17..2020-10-29&type=Issues) | [@minrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aminrk+updated%3A2020-01-17..2020-10-29&type=Issues) | [@mriedem](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Amriedem+updated%3A2020-01-17..2020-10-29&type=Issues) | [@nscozzaro](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Anscozzaro+updated%3A2020-01-17..2020-10-29&type=Issues) | [@pabepadu](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apabepadu+updated%3A2020-01-17..2020-10-29&type=Issues) | [@possiblyMikeB](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ApossiblyMikeB+updated%3A2020-01-17..2020-10-29&type=Issues) | [@psyvision](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Apsyvision+updated%3A2020-01-17..2020-10-29&type=Issues) | [@rabsr](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arabsr+updated%3A2020-01-17..2020-10-29&type=Issues) | [@rainwoodman](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arainwoodman+updated%3A2020-01-17..2020-10-29&type=Issues) | [@rajat404](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arajat404+updated%3A2020-01-17..2020-10-29&type=Issues) | [@rcthomas](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arcthomas+updated%3A2020-01-17..2020-10-29&type=Issues) | [@reneluria](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Areneluria+updated%3A2020-01-17..2020-10-29&type=Issues) | [@rgbkrk](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Argbkrk+updated%3A2020-01-17..2020-10-29&type=Issues) | [@rkdarst](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arkdarst+updated%3A2020-01-17..2020-10-29&type=Issues) | [@rkevin-arch](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Arkevin-arch+updated%3A2020-01-17..2020-10-29&type=Issues) | [@romainx](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aromainx+updated%3A2020-01-17..2020-10-29&type=Issues) | [@ryanlovett](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aryanlovett+updated%3A2020-01-17..2020-10-29&type=Issues) | [@ryogesh](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aryogesh+updated%3A2020-01-17..2020-10-29&type=Issues) | [@sdague](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asdague+updated%3A2020-01-17..2020-10-29&type=Issues) | [@snickell](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asnickell+updated%3A2020-01-17..2020-10-29&type=Issues) | [@SonakshiGrover](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3ASonakshiGrover+updated%3A2020-01-17..2020-10-29&type=Issues) | [@ssanderson](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Assanderson+updated%3A2020-01-17..2020-10-29&type=Issues) | [@stefanvangastel](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Astefanvangastel+updated%3A2020-01-17..2020-10-29&type=Issues) | [@steinad](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asteinad+updated%3A2020-01-17..2020-10-29&type=Issues) | [@stephen-a2z](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Astephen-a2z+updated%3A2020-01-17..2020-10-29&type=Issues) | [@stevegore](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Astevegore+updated%3A2020-01-17..2020-10-29&type=Issues) | [@stv0g](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Astv0g+updated%3A2020-01-17..2020-10-29&type=Issues) | [@subgero](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asubgero+updated%3A2020-01-17..2020-10-29&type=Issues) | [@sudi007](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asudi007+updated%3A2020-01-17..2020-10-29&type=Issues) | [@summerswallow](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asummerswallow+updated%3A2020-01-17..2020-10-29&type=Issues) | [@support](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asupport+updated%3A2020-01-17..2020-10-29&type=Issues) | [@synchronizing](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Asynchronizing+updated%3A2020-01-17..2020-10-29&type=Issues) | [@thuvh](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Athuvh+updated%3A2020-01-17..2020-10-29&type=Issues) | [@tritemio](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atritemio+updated%3A2020-01-17..2020-10-29&type=Issues) | [@twalcari](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Atwalcari+updated%3A2020-01-17..2020-10-29&type=Issues) | [@vchandvankar](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Avchandvankar+updated%3A2020-01-17..2020-10-29&type=Issues) | [@vilhelmen](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Avilhelmen+updated%3A2020-01-17..2020-10-29&type=Issues) | [@vlizanae](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Avlizanae+updated%3A2020-01-17..2020-10-29&type=Issues) | [@weimin](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aweimin+updated%3A2020-01-17..2020-10-29&type=Issues) | [@welcome](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awelcome+updated%3A2020-01-17..2020-10-29&type=Issues) | [@willingc](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Awillingc+updated%3A2020-01-17..2020-10-29&type=Issues) | [@xlotlu](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Axlotlu+updated%3A2020-01-17..2020-10-29&type=Issues) | [@yhal-nesi](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayhal-nesi+updated%3A2020-01-17..2020-10-29&type=Issues) | [@ynnelson](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Aynnelson+updated%3A2020-01-17..2020-10-29&type=Issues) | [@yuvipanda](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Ayuvipanda+updated%3A2020-01-17..2020-10-29&type=Issues) | [@zonca](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3Azonca+updated%3A2020-01-17..2020-10-29&type=Issues) | [@Zsailer](https://github.com/search?q=repo%3Ajupyterhub%2Fjupyterhub+involves%3AZsailer+updated%3A2020-01-17..2020-10-29&type=Issues)

## 1.1

### [1.1.0] 2020-01-17

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

- LocalProcessSpawner should work on windows by using psutil.pid_exists [#2882](https://github.com/jupyterhub/jupyterhub/pull/2882) ([@ociule](https://github.com/ociule))
- trigger auth_state_hook prior to options form, add auth_state to template namespace [#2881](https://github.com/jupyterhub/jupyterhub/pull/2881) ([@minrk](https://github.com/minrk))
- Added guide 'install jupyterlab the hard way' #2110 [#2842](https://github.com/jupyterhub/jupyterhub/pull/2842) ([@mangecoeur](https://github.com/mangecoeur))
- Add prometheus metric to measure hub startup time [#2799](https://github.com/jupyterhub/jupyterhub/pull/2799) ([@rajat404](https://github.com/rajat404))
- Add Spawner.auth_state_hook [#2555](https://github.com/jupyterhub/jupyterhub/pull/2555) ([@rcthomas](https://github.com/rcthomas))
- Link services from jupyterhub pages [#2763](https://github.com/jupyterhub/jupyterhub/pull/2763) ([@rcthomas](https://github.com/rcthomas))
- `JupyterHub.user_redirect_hook` is added to allow admins to customize /user-redirect/ behavior [#2790](https://github.com/jupyterhub/jupyterhub/pull/2790) ([@yuvipanda](https://github.com/yuvipanda))
- Add prometheus metric to measure hub startup time [#2799](https://github.com/jupyterhub/jupyterhub/pull/2799) ([@rajat404](https://github.com/rajat404))
- Add prometheus metric to measure proxy route poll times [#2798](https://github.com/jupyterhub/jupyterhub/pull/2798) ([@rajat404](https://github.com/rajat404))
- `PROXY_DELETE_DURATION_SECONDS` prometheus metric is added, to measure proxy route deletion times [#2788](https://github.com/jupyterhub/jupyterhub/pull/2788) ([@rajat404](https://github.com/rajat404))
- `Service.oauth_no_confirm` is added, it is useful for admin-managed services that are considered part of the Hub and shouldn't need to prompt the user for access [#2767](https://github.com/jupyterhub/jupyterhub/pull/2767) ([@minrk](https://github.com/minrk))
- `JupyterHub.default_server_name` is added to make the default server be a named server with provided name [#2735](https://github.com/jupyterhub/jupyterhub/pull/2735) ([@krinsman](https://github.com/krinsman))
- `JupyterHub.init_spawners_timeout` is introduced to combat slow startups on large JupyterHub deployments [#2721](https://github.com/jupyterhub/jupyterhub/pull/2721) ([@minrk](https://github.com/minrk))
- The configuration `uids` for local authenticators is added to consistently assign users UNIX id's between installations [#2687](https://github.com/jupyterhub/jupyterhub/pull/2687) ([@rgerkin](https://github.com/rgerkin))
- `JupyterHub.activity_resolution` is introduced with a default value of 30s improving performance by not updating the database with user activity too often [#2605](https://github.com/jupyterhub/jupyterhub/pull/2605) ([@minrk](https://github.com/minrk))
- [HubAuth](jupyterhub.services.auth.HubAuth)'s SSL configuration can now be set through environment variables [#2588](https://github.com/jupyterhub/jupyterhub/pull/2588) ([@cmd-ntrf](https://github.com/cmd-ntrf))
- Expose spawner.user_options in REST API. [#2755](https://github.com/jupyterhub/jupyterhub/pull/2755) ([@danielballan](https://github.com/danielballan))
- add block for scripts included in head [#2828](https://github.com/jupyterhub/jupyterhub/pull/2828) ([@bitnik](https://github.com/bitnik))
- Instrument JupyterHub to record events with jupyter_telemetry [Part II] [#2698](https://github.com/jupyterhub/jupyterhub/pull/2698) ([@Zsailer](https://github.com/Zsailer))
- Make announcements visible without custom HTML [#2570](https://github.com/jupyterhub/jupyterhub/pull/2570) ([@consideRatio](https://github.com/consideRatio))
- Display server version on admin page [#2776](https://github.com/jupyterhub/jupyterhub/pull/2776) ([@vilhelmen](https://github.com/vilhelmen))

#### Fixes

- Bugfix: pam_normalize_username didn't return username [#2876](https://github.com/jupyterhub/jupyterhub/pull/2876) ([@rkdarst](https://github.com/rkdarst))
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

- Optimize CI jobs and default to bionic [#2897](https://github.com/jupyterhub/jupyterhub/pull/2897) ([@consideRatio](https://github.com/consideRatio))
- catch connection error for ssl failures [#2889](https://github.com/jupyterhub/jupyterhub/pull/2889) ([@minrk](https://github.com/minrk))
- Fix implementation of default server name [#2887](https://github.com/jupyterhub/jupyterhub/pull/2887) ([@krinsman](https://github.com/krinsman))
- fixup allow_failures [#2880](https://github.com/jupyterhub/jupyterhub/pull/2880) ([@minrk](https://github.com/minrk))
- Pass tests on Python 3.8 [#2879](https://github.com/jupyterhub/jupyterhub/pull/2879) ([@minrk](https://github.com/minrk))
- Fixup .travis.yml [#2868](https://github.com/jupyterhub/jupyterhub/pull/2868) ([@consideRatio](https://github.com/consideRatio))
- Update README's badges [#2867](https://github.com/jupyterhub/jupyterhub/pull/2867) ([@consideRatio](https://github.com/consideRatio))
- Dockerfile: add build-essential to builder image [#2866](https://github.com/jupyterhub/jupyterhub/pull/2866) ([@rkdarst](https://github.com/rkdarst))
- Dockerfile: Copy share/ to the final image [#2864](https://github.com/jupyterhub/jupyterhub/pull/2864) ([@rkdarst](https://github.com/rkdarst))
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
- block urllib3 versions with encoding bug [#2743](https://github.com/jupyterhub/jupyterhub/pull/2743) ([@minrk](https://github.com/minrk))
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

  ![named servers on the home page](/images/named-servers-home.png)

- Authenticators can now expire and refresh authentication data by implementing
  `Authenticator.refresh_user(user)`.
  This allows things like OAuth data and access tokens to be refreshed.
  When used together with `Authenticator.refresh_pre_spawn = True`,
  auth refresh can be forced prior to Spawn,
  allowing the Authenticator to _require_ that authentication data is fresh
  immediately before the user's server is launched.

```{seealso}

  - {meth}`.Authenticator.refresh_user`
  - {meth}`.Spawner.create_certs`
  - {meth}`.Spawner.move_certs`
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
  or custom allowed/blocked logic.
  This hook is called _after_ existing normalization and allowed-username checking.
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
  This is meant to make it _easier_ to contribute to JupyterHub,
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

- Fixes an issue that required all running user servers to be restarted
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
- Add `Authenticator.blacklist` for blocking users instead of allowing.
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
- Admin requests for `/user/:name` (when admin-access is enabled) launch the right server if it's not running instead of redirecting to their own.
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
- Add logging of error if adding users already in database. [\#689](https://github.com/jupyterhub/jupyterhub/pull/689)
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
- Removed deprecated SwarmSpawner link. [\#699](https://github.com/jupyterhub/jupyterhub/pull/699)

## 0.6

### [0.6.1] - 2016-05-04

Bugfixes on 0.6:

- statsd is an optional dependency, only needed if in use
- Notice more quickly when servers have crashed
- Better error pages for proxy errors
- Add Stop All button to admin panel for stopping all servers at once

### [0.6.0] - 2016-04-25

- JupyterHub has moved to a new `jupyterhub` namespace on GitHub and Docker. What was `jupyter/jupyterhub` is now `jupyterhub/jupyterhub`, etc.
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

[unreleased]: https://github.com/jupyterhub/jupyterhub/compare/5.1.0...HEAD
[3.0.0]: https://github.com/jupyterhub/jupyterhub/compare/2.3.1...3.0.0
[2.3.1]: https://github.com/jupyterhub/jupyterhub/compare/2.3.0...2.3.1
[2.3.0]: https://github.com/jupyterhub/jupyterhub/compare/2.2.2...2.3.0
[2.2.2]: https://github.com/jupyterhub/jupyterhub/compare/2.2.1...2.2.2
[2.2.1]: https://github.com/jupyterhub/jupyterhub/compare/2.2.0...2.2.1
[2.2.0]: https://github.com/jupyterhub/jupyterhub/compare/2.1.1...2.2.0
[2.1.1]: https://github.com/jupyterhub/jupyterhub/compare/2.1.0...2.1.1
[2.1.0]: https://github.com/jupyterhub/jupyterhub/compare/2.0.2...2.1.0
[2.0.2]: https://github.com/jupyterhub/jupyterhub/compare/2.0.1...2.0.2
[2.0.1]: https://github.com/jupyterhub/jupyterhub/compare/2.0.0...2.0.1
[2.0.0]: https://github.com/jupyterhub/jupyterhub/compare/1.5.0...2.0.0
[1.5.0]: https://github.com/jupyterhub/jupyterhub/compare/1.4.2...1.5.0
[1.4.2]: https://github.com/jupyterhub/jupyterhub/compare/1.4.1...1.4.2
[1.4.1]: https://github.com/jupyterhub/jupyterhub/compare/1.4.0...1.4.1
[1.4.0]: https://github.com/jupyterhub/jupyterhub/compare/1.3.0...1.4.0
[1.3.0]: https://github.com/jupyterhub/jupyterhub/compare/1.2.1...1.3.0
[1.2.2]: https://github.com/jupyterhub/jupyterhub/compare/1.2.1...1.2.2
[1.2.1]: https://github.com/jupyterhub/jupyterhub/compare/1.2.0...1.2.1
[1.2.0]: https://github.com/jupyterhub/jupyterhub/compare/1.1.0...1.2.0
[1.1.0]: https://github.com/jupyterhub/jupyterhub/compare/1.0.0...1.1.0
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
