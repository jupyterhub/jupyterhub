# Notes from API Review

## General

- descriptions change ok? without violating user API contract
- should 'https' be added to schemes?
- TODO: check against functions in source code

## API Specific

- [ ] /info

      * Should we add that authentication is needed

- [ ] POST /users

      * creates multiple users sets both username and whether user has admin access

- [ ] POST /users/{name}

      * create a single user (no admin mention in parameters currently; should there be
        a data section under parameters with schema of both properties?)

- [ ] PATCH /users/{name}

      * clarify the optional keys

- [ ] POST /users/{name}/admin-access

      * clarify that the admin access is only for the named user
      * Do we need a change/toggle or should we change POST to set
      * Do we need a GET admin access?

- [ ] /groups/{name}

      * Should we add PATCH to modify name of group

- [ ] /groups/{name}/users

      * Should we add GET or will it automagically provide the list of users in
        the named group

- [ ] /proxy

      * Will users think that PATCH also performs the sync done in POST?

- [ ] /shutdown

      * Do we log (I suspect we do) what is shutdown (hub, proxy, notebook servers)?

## Add to documentation

- base url
- test for connectivity to API (unauth '/' and auth '/info')