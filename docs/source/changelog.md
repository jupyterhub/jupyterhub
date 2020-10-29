# Changelog

For detailed changes from the prior release, click on the version number, and
its link will bring up a GitHub listing of changes. Use `git log` on the
command line for details.


## [Unreleased]

## 1.2

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
* make pagination configurable [#3229](https://github.com/jupyterhub/jupyterhub/pull/3229) ([@minrk](https://github.com/minrk))
* Make api_request to CHP's REST API more reliable [#3223](https://github.com/jupyterhub/jupyterhub/pull/3223) ([@consideRatio](https://github.com/consideRatio))
* Control service display [#3160](https://github.com/jupyterhub/jupyterhub/pull/3160) ([@rcthomas](https://github.com/rcthomas))
* Add a footer block + wrap the admin footer in this block [#3136](https://github.com/jupyterhub/jupyterhub/pull/3136) ([@pabepadu](https://github.com/pabepadu))
* Allow JupyterHub.default_url to be a callable [#3133](https://github.com/jupyterhub/jupyterhub/pull/3133) ([@danlester](https://github.com/danlester))
* Allow head requests for the health endpoint [#3131](https://github.com/jupyterhub/jupyterhub/pull/3131) ([@rkevin-arch](https://github.com/rkevin-arch))
* Hide hamburger button menu in mobile/responsive mode and fix other minor issues [#3103](https://github.com/jupyterhub/jupyterhub/pull/3103) ([@kinow](https://github.com/kinow))
* build jupyterhub/jupyterhub-demo image on docker hub [#3083](https://github.com/jupyterhub/jupyterhub/pull/3083) ([@minrk](https://github.com/minrk))
* Add JupyterHub Demo docker image [#3059](https://github.com/jupyterhub/jupyterhub/pull/3059) ([@GeorgianaElena](https://github.com/GeorgianaElena))
* Warn if both bind_url and ip/port/base_url are set [#3057](https://github.com/jupyterhub/jupyterhub/pull/3057) ([@GeorgianaElena](https://github.com/GeorgianaElena))
* UI Feedback on Submit [#3028](https://github.com/jupyterhub/jupyterhub/pull/3028) ([@possiblyMikeB](https://github.com/possiblyMikeB))
* Support kubespawner running on a IPv6 only cluster [#3020](https://github.com/jupyterhub/jupyterhub/pull/3020) ([@stv0g](https://github.com/stv0g))
* Spawn with options passed in query arguments to /spawn [#3013](https://github.com/jupyterhub/jupyterhub/pull/3013) ([@twalcari](https://github.com/twalcari))
* SpawnHandler POST with user form options displays the spawn-pending page [#2978](https://github.com/jupyterhub/jupyterhub/pull/2978) ([@danlester](https://github.com/danlester))
* Start named servers by pressing the Enter key [#2960](https://github.com/jupyterhub/jupyterhub/pull/2960) ([@jtpio](https://github.com/jtpio))
* Keep the URL fragments after spawning an application [#2952](https://github.com/jupyterhub/jupyterhub/pull/2952) ([@kinow](https://github.com/kinow))
* Allow implicit spawn via javascript redirect [#2941](https://github.com/jupyterhub/jupyterhub/pull/2941) ([@minrk](https://github.com/minrk))
* make init_spawners check O(running servers) not O(total users) [#2936](https://github.com/jupyterhub/jupyterhub/pull/2936) ([@minrk](https://github.com/minrk))
* Add favicon to the base page template [#2930](https://github.com/jupyterhub/jupyterhub/pull/2930) ([@JohnPaton](https://github.com/JohnPaton))
* Adding pagination in the admin panel [#2929](https://github.com/jupyterhub/jupyterhub/pull/2929) ([@cbjuan](https://github.com/cbjuan))
* Generate prometheus metrics docs [#2891](https://github.com/jupyterhub/jupyterhub/pull/2891) ([@rajat404](https://github.com/rajat404))
* Add support for Jupyter Server [#2601](https://github.com/jupyterhub/jupyterhub/pull/2601) ([@yuvipanda](https://github.com/yuvipanda))

#### Bugs fixed
* Fix #2284 must be sent from authorization page [#3219](https://github.com/jupyterhub/jupyterhub/pull/3219) ([@elgalu](https://github.com/elgalu))
* avoid specifying default_value=None in Command traits [#3208](https://github.com/jupyterhub/jupyterhub/pull/3208) ([@minrk](https://github.com/minrk))
* Prevent OverflowErrors in exponential_backoff() [#3204](https://github.com/jupyterhub/jupyterhub/pull/3204) ([@kreuzert](https://github.com/kreuzert))
* update prometheus metrics for server spawn when it fails with exception [#3150](https://github.com/jupyterhub/jupyterhub/pull/3150) ([@yhal-nesi](https://github.com/yhal-nesi))
* jupyterhub/utils: Load system default CA certificates in make_ssl_context [#3140](https://github.com/jupyterhub/jupyterhub/pull/3140) ([@chancez](https://github.com/chancez))
* admin page sorts on spawner last_activity instead of user last_activity [#3137](https://github.com/jupyterhub/jupyterhub/pull/3137) ([@lydian](https://github.com/lydian))
* Fix the services dropdown on the admin page [#3132](https://github.com/jupyterhub/jupyterhub/pull/3132) ([@pabepadu](https://github.com/pabepadu))
* Don't log a warning when slow_spawn_timeout is disabled [#3127](https://github.com/jupyterhub/jupyterhub/pull/3127) ([@mriedem](https://github.com/mriedem))
* app.py: Work around incompatibility between Tornado 6 and asyncio proactor event loop in python 3.8 on Windows [#3123](https://github.com/jupyterhub/jupyterhub/pull/3123) ([@alexweav](https://github.com/alexweav))
* jupyterhub/user: clear spawner state after post_stop_hook [#3121](https://github.com/jupyterhub/jupyterhub/pull/3121) ([@rkdarst](https://github.com/rkdarst))
* fix for stopping named server deleting default server and tests [#3109](https://github.com/jupyterhub/jupyterhub/pull/3109) ([@kxiao-fn](https://github.com/kxiao-fn))
* Hide hamburger button menu in mobile/responsive mode and fix other minor issues [#3103](https://github.com/jupyterhub/jupyterhub/pull/3103) ([@kinow](https://github.com/kinow))
* Rename Authenticator.white/blacklist to allowed/blocked [#3090](https://github.com/jupyterhub/jupyterhub/pull/3090) ([@minrk](https://github.com/minrk))
* Include the query string parameters when redirecting to a new URL [#3089](https://github.com/jupyterhub/jupyterhub/pull/3089) ([@kinow](https://github.com/kinow))
* Make `delete_invalid_users` configurable [#3087](https://github.com/jupyterhub/jupyterhub/pull/3087) ([@fcollonval](https://github.com/fcollonval))
* Ensure client dependencies build before wheel [#3082](https://github.com/jupyterhub/jupyterhub/pull/3082) ([@diurnalist](https://github.com/diurnalist))
* make Spawner.environment config highest priority [#3081](https://github.com/jupyterhub/jupyterhub/pull/3081) ([@minrk](https://github.com/minrk))
* Changing start my server button link to spawn url once server is stopped [#3042](https://github.com/jupyterhub/jupyterhub/pull/3042) ([@rabsr](https://github.com/rabsr))
* Fix CSS on admin page version listing [#3035](https://github.com/jupyterhub/jupyterhub/pull/3035) ([@vilhelmen](https://github.com/vilhelmen))
* Fix user_row endblock in admin template [#3015](https://github.com/jupyterhub/jupyterhub/pull/3015) ([@jtpio](https://github.com/jtpio))
* Fix --generate-config bug when specifying a filename [#2907](https://github.com/jupyterhub/jupyterhub/pull/2907) ([@consideRatio](https://github.com/consideRatio))
* Handle the protocol when ssl is enabled and log the right URL [#2773](https://github.com/jupyterhub/jupyterhub/pull/2773) ([@kinow](https://github.com/kinow))

#### Maintenance and upkeep improvements
* Update travis-ci badge in README.md [#3232](https://github.com/jupyterhub/jupyterhub/pull/3232) ([@consideRatio](https://github.com/consideRatio))
* stop building docs on circleci [#3209](https://github.com/jupyterhub/jupyterhub/pull/3209) ([@minrk](https://github.com/minrk))
* Upgraded Jquery dep [#3174](https://github.com/jupyterhub/jupyterhub/pull/3174) ([@AngelOnFira](https://github.com/AngelOnFira))
* Don't allow 'python:3.8 + master dependencies' to fail [#3157](https://github.com/jupyterhub/jupyterhub/pull/3157) ([@manics](https://github.com/manics))
* Update Dockerfile to ubuntu:focal (Python 3.8) [#3156](https://github.com/jupyterhub/jupyterhub/pull/3156) ([@manics](https://github.com/manics))
* Simplify code of the health check handler [#3149](https://github.com/jupyterhub/jupyterhub/pull/3149) ([@betatim](https://github.com/betatim))
* Get error description from error key vs error_description key [#3147](https://github.com/jupyterhub/jupyterhub/pull/3147) ([@jgwerner](https://github.com/jgwerner))
* Implement singleuser with mixins [#3128](https://github.com/jupyterhub/jupyterhub/pull/3128) ([@minrk](https://github.com/minrk))
* only build tagged versions on docker tags [#3118](https://github.com/jupyterhub/jupyterhub/pull/3118) ([@minrk](https://github.com/minrk))
* Log slow_stop_timeout when hit like slow_spawn_timeout [#3111](https://github.com/jupyterhub/jupyterhub/pull/3111) ([@mriedem](https://github.com/mriedem))
* loosen jupyter-telemetry pin [#3102](https://github.com/jupyterhub/jupyterhub/pull/3102) ([@minrk](https://github.com/minrk))
* Remove old context-less print statement [#3100](https://github.com/jupyterhub/jupyterhub/pull/3100) ([@mriedem](https://github.com/mriedem))
* Allow `python:3.8 + master dependencies` to fail [#3079](https://github.com/jupyterhub/jupyterhub/pull/3079) ([@manics](https://github.com/manics))
* Test with some master dependencies. [#3076](https://github.com/jupyterhub/jupyterhub/pull/3076) ([@Carreau](https://github.com/Carreau))
* synchronize implementation of expiring values [#3072](https://github.com/jupyterhub/jupyterhub/pull/3072) ([@minrk](https://github.com/minrk))
* More consistent behavior for UserDict.get and `key in UserDict` [#3071](https://github.com/jupyterhub/jupyterhub/pull/3071) ([@minrk](https://github.com/minrk))
* pin jupyter_telemetry dependency [#3067](https://github.com/jupyterhub/jupyterhub/pull/3067) ([@Zsailer](https://github.com/Zsailer))
* Use the issue templates from the central repo [#3056](https://github.com/jupyterhub/jupyterhub/pull/3056) ([@GeorgianaElena](https://github.com/GeorgianaElena))
* Update links to the black GitHub repository [#3054](https://github.com/jupyterhub/jupyterhub/pull/3054) ([@jtpio](https://github.com/jtpio))
* Log successful /health requests as debug level [#3047](https://github.com/jupyterhub/jupyterhub/pull/3047) ([@consideRatio](https://github.com/consideRatio))
* Fix broken test due to BeautifulSoup 4.9.0 behavior change [#3025](https://github.com/jupyterhub/jupyterhub/pull/3025) ([@twalcari](https://github.com/twalcari))
* Remove unused imports [#3019](https://github.com/jupyterhub/jupyterhub/pull/3019) ([@stv0g](https://github.com/stv0g))
* Use pip instead of conda for building the docs on RTD [#3010](https://github.com/jupyterhub/jupyterhub/pull/3010) ([@GeorgianaElena](https://github.com/GeorgianaElena))
* Avoid redundant logging of jupyterhub version mismatches [#2971](https://github.com/jupyterhub/jupyterhub/pull/2971) ([@mriedem](https://github.com/mriedem))
* Add .vscode to gitignore [#2959](https://github.com/jupyterhub/jupyterhub/pull/2959) ([@jtpio](https://github.com/jtpio))
* preserve auth type when logging obfuscated auth header [#2953](https://github.com/jupyterhub/jupyterhub/pull/2953) ([@minrk](https://github.com/minrk))
* make spawner:server relationship explicitly one to one [#2944](https://github.com/jupyterhub/jupyterhub/pull/2944) ([@minrk](https://github.com/minrk))
* Add what we need with some margin to Dockerfile's build stage [#2905](https://github.com/jupyterhub/jupyterhub/pull/2905) ([@consideRatio](https://github.com/consideRatio))
* bump reorder-imports hook [#2899](https://github.com/jupyterhub/jupyterhub/pull/2899) ([@minrk](https://github.com/minrk))

#### Documentation improvements
* Fix typo in documentation [#3226](https://github.com/jupyterhub/jupyterhub/pull/3226) ([@xlotlu](https://github.com/xlotlu))
* [docs] Remove duplicate line in changelog for 1.1.0  [#3207](https://github.com/jupyterhub/jupyterhub/pull/3207) ([@kinow](https://github.com/kinow))
* changelog for 1.2.0b1 [#3192](https://github.com/jupyterhub/jupyterhub/pull/3192) ([@consideRatio](https://github.com/consideRatio))
* Add SELinux configuration for nginx [#3185](https://github.com/jupyterhub/jupyterhub/pull/3185) ([@rainwoodman](https://github.com/rainwoodman))
* Mention the PAM pitfall on fedora. [#3184](https://github.com/jupyterhub/jupyterhub/pull/3184) ([@rainwoodman](https://github.com/rainwoodman))
* Added extra documentation for endpoint /users/{name}/servers/{server_name}. [#3159](https://github.com/jupyterhub/jupyterhub/pull/3159) ([@synchronizing](https://github.com/synchronizing))
* docs: please docs linter (move_cert docstring) [#3151](https://github.com/jupyterhub/jupyterhub/pull/3151) ([@consideRatio](https://github.com/consideRatio))
* Needed NoEsacpe (NE)  option for apache [#3143](https://github.com/jupyterhub/jupyterhub/pull/3143) ([@basvandervlies](https://github.com/basvandervlies))
* Document external service api_tokens better [#3142](https://github.com/jupyterhub/jupyterhub/pull/3142) ([@snickell](https://github.com/snickell))
* Remove idle culler example [#3114](https://github.com/jupyterhub/jupyterhub/pull/3114) ([@yuvipanda](https://github.com/yuvipanda))
* docs: unsqueeze logo, remove unused CSS and templates [#3107](https://github.com/jupyterhub/jupyterhub/pull/3107) ([@consideRatio](https://github.com/consideRatio))
* Update version in docs/rest-api.yaml [#3104](https://github.com/jupyterhub/jupyterhub/pull/3104) ([@cmd-ntrf](https://github.com/cmd-ntrf))
* Replace zonca/remotespawner with NERSC/sshspawner [#3086](https://github.com/jupyterhub/jupyterhub/pull/3086) ([@manics](https://github.com/manics))
* Remove already done named servers from roadmap [#3084](https://github.com/jupyterhub/jupyterhub/pull/3084) ([@elgalu](https://github.com/elgalu))
* proxy settings might cause authentication errors [#3078](https://github.com/jupyterhub/jupyterhub/pull/3078) ([@gatoniel](https://github.com/gatoniel))
* Add Configuration Reference section to docs [#3077](https://github.com/jupyterhub/jupyterhub/pull/3077) ([@kinow](https://github.com/kinow))
* document upgrading from api_tokens to services config [#3055](https://github.com/jupyterhub/jupyterhub/pull/3055) ([@minrk](https://github.com/minrk))
* [Docs] Disable proxy_buffering when using nginx reverse proxy [#3048](https://github.com/jupyterhub/jupyterhub/pull/3048) ([@mhwasil](https://github.com/mhwasil))
* docs: add proxy_http_version 1.1 [#3046](https://github.com/jupyterhub/jupyterhub/pull/3046) ([@ceocoder](https://github.com/ceocoder))
* #1018 PAM added in prerequisites [#3040](https://github.com/jupyterhub/jupyterhub/pull/3040) ([@romainx](https://github.com/romainx))
* Fix use of auxiliary verb on index.rst [#3022](https://github.com/jupyterhub/jupyterhub/pull/3022) ([@joshmeek](https://github.com/joshmeek))
* Fix docs CI test failure: duplicate object description [#3021](https://github.com/jupyterhub/jupyterhub/pull/3021) ([@rkdarst](https://github.com/rkdarst))
* Update issue templates [#3001](https://github.com/jupyterhub/jupyterhub/pull/3001) ([@GeorgianaElena](https://github.com/GeorgianaElena))
* fix wrong name on firewall [#2997](https://github.com/jupyterhub/jupyterhub/pull/2997) ([@thuvh](https://github.com/thuvh))
* updating docs theme [#2995](https://github.com/jupyterhub/jupyterhub/pull/2995) ([@choldgraf](https://github.com/choldgraf))
* Update contributor docs [#2972](https://github.com/jupyterhub/jupyterhub/pull/2972) ([@mriedem](https://github.com/mriedem))
* Server.user_options rest-api documented [#2966](https://github.com/jupyterhub/jupyterhub/pull/2966) ([@mriedem](https://github.com/mriedem))
* Pin sphinx theme [#2956](https://github.com/jupyterhub/jupyterhub/pull/2956) ([@manics](https://github.com/manics))
* [doc] Fix couple typos in the documentation [#2951](https://github.com/jupyterhub/jupyterhub/pull/2951) ([@kinow](https://github.com/kinow))
* Docs: Fixed grammar on landing page [#2950](https://github.com/jupyterhub/jupyterhub/pull/2950) ([@alexdriedger](https://github.com/alexdriedger))
* add general faq [#2946](https://github.com/jupyterhub/jupyterhub/pull/2946) ([@minrk](https://github.com/minrk))
* docs: use metachannel for faster environment solve [#2943](https://github.com/jupyterhub/jupyterhub/pull/2943) ([@minrk](https://github.com/minrk))
* update docs environments [#2942](https://github.com/jupyterhub/jupyterhub/pull/2942) ([@minrk](https://github.com/minrk))
* [doc] Add more docs about Cookies used for authentication in JupyterHub [#2940](https://github.com/jupyterhub/jupyterhub/pull/2940) ([@kinow](https://github.com/kinow))
* [doc] Use fixed commit plus line number in github link [#2939](https://github.com/jupyterhub/jupyterhub/pull/2939) ([@kinow](https://github.com/kinow))
* [doc] Fix link to SSL encryption from troubleshooting page [#2938](https://github.com/jupyterhub/jupyterhub/pull/2938) ([@kinow](https://github.com/kinow))
* rest api: fix schema for remove parameter in rest api [#2917](https://github.com/jupyterhub/jupyterhub/pull/2917) ([@minrk](https://github.com/minrk))
* Add troubleshooting topics [#2914](https://github.com/jupyterhub/jupyterhub/pull/2914) ([@jgwerner](https://github.com/jgwerner))
* Several fixes to the doc [#2904](https://github.com/jupyterhub/jupyterhub/pull/2904) ([@reneluria](https://github.com/reneluria))
* fix: 'Non-ASCII character '\xc3' [#2901](https://github.com/jupyterhub/jupyterhub/pull/2901) ([@jgwerner](https://github.com/jgwerner))
* Generate prometheus metrics docs [#2891](https://github.com/jupyterhub/jupyterhub/pull/2891) ([@rajat404](https://github.com/rajat404))

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
- [HubAuth](https://jupyterhub.readthedocs.io/en/stable/api/services.auth.html#jupyterhub.services.auth.HubAuth)'s SSL configuration can now be set through environment variables [#2588](https://github.com/jupyterhub/jupyterhub/pull/2588) ([@cmd-ntrf](https://github.com/cmd-ntrf))
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
  or custom allowed/blocked logic.
  This hook is called *after* existing normalization and allowed-username checking.
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


[Unreleased]: https://github.com/jupyterhub/jupyterhub/compare/1.2.0...HEAD
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
