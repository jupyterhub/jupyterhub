{{- /*
    As we found Helm chart configuration of JupyterHub authentication was
    too complicated both to maintain and use in its badly maintained state,
    we sharply transitioned to a new system in 0.11.0.

    To help users transition, this file was developed. It converts the old
    auth configuration under "auth" to the new under "c". We detect if the
    old system is used and let the Helm chart's template rendering fail
    where we also provide a useful error message including the new config
    to use in its place.

    Implementation details:
    - Secret content must be censored
    - auth.state.cryptoKey needs a new home
*/}}

{{- define "jupyterhub.authDep.classKeyToLong.map" }}
google: google
github: github
cilogon: cilogon
gitlab: gitlab
azuread: azuread
mediawiki: mediawiki
globus: globus
hmac: hmacauthenticator.HMACAuthenticator
dummy: dummy
tmp: tmpauthenticator.TmpAuthenticator
lti: ltiauthenticator.LTIAuthenticator
ldap: ldapauthenticator.LDAPAuthenticator
{{- end }}

{{- /* Uses the map above, taking a keys, returning a value. */}}
{{- define "jupyterhub.authDep.classKeyToLong" -}}
    {{- $map := include "jupyterhub.authDep.classKeyToLong.map" . | fromYaml }}
    {{- index $map . }}
{{- end }}

{{- define "jupyterhub.authDep.remapOldToNew.map" }}
scopes: OAuthenticator.scope
state.enabled: Authenticator.enable_auth_state
state.cryptoKey: CryptKeeper.keys
admin.access: JupyterHub.admin_access
admin.users: Authenticator.admin_users
whitelist.users: Authenticator.allowed_users
allowedUsers: Authenticator.allowed_users
google.clientId: GoogleOAuthenticator.client_id
google.clientSecret: GoogleOAuthenticator.client_secret
google.callbackUrl: GoogleOAuthenticator.oauth_callback_url
google.hostedDomain: GoogleOAuthenticator.hosted_domain
google.loginService: GoogleOAuthenticator.login_service
github.clientId: GitHubOAuthenticator.client_id
github.clientSecret: GitHubOAuthenticator.client_secret
github.callbackUrl: GitHubOAuthenticator.oauth_callback_url
github.orgWhitelist: GitHubOAuthenticator.allowed_organizations
github.allowedOrganizations: GitHubOAuthenticator.allowed_organizations
cilogon.clientId: CILogonOAuthenticator.client_id
cilogon.clientSecret: CILogonOAuthenticator.client_secret
cilogon.callbackUrl: CILogonOAuthenticator.oauth_callback_url
gitlab.clientId: GitLabOAuthenticator.client_id
gitlab.clientSecret: GitLabOAuthenticator.client_secret
gitlab.callbackUrl: GitLabOAuthenticator.oauth_callback_url
gitlab.gitlabGroupWhitelist: GitLabOAuthenticator.allowed_gitlab_groups
gitlab.allowedGitlabGroups: GitLabOAuthenticator.allowed_gitlab_groups
gitlab.gitlabProjectIdWhitelist: GitLabOAuthenticator.allowed_project_ids
gitlab.allowedProjectIds: GitLabOAuthenticator.allowed_project_ids
gitlab.gitlabUrl: GitLabOAuthenticator.gitlab_url
azuread.clientId: AzureAdOAuthenticator.client_id
azuread.clientSecret: AzureAdOAuthenticator.client_secret
azuread.callbackUrl: AzureAdOAuthenticator.oauth_callback_url
azuread.tenantId: AzureAdOAuthenticator.tenant_id
azuread.usernameClaim: AzureAdOAuthenticator.username_claim
mediawiki.clientId: MWOAuthenticator.client_id
mediawiki.clientSecret: MWOAuthenticator.client_secret
mediawiki.callbackUrl: MWOAuthenticator.oauth_callback_url
mediawiki.indexUrl: MWOAuthenticator.index_url
globus.clientId: GlobusOAuthenticator.client_id
globus.clientSecret: GlobusOAuthenticator.client_secret
globus.callbackUrl: GlobusOAuthenticator.oauth_callback_url
hmac.secretKey: HMACAuthenticator.secret_key
dummy.password: DummyAuthenticator.password
lti.consumers: LTIAuthenticator.consumers
ldap.server.address: LDAPAuthenticator.server_address
ldap.server.port: LDAPAuthenticator.server_port
ldap.server.ssl: LDAPAuthenticator.use_ssl
ldap.allowedGroups: LDAPAuthenticator.allowed_groups
ldap.dn.templates: LDAPAuthenticator.bind_dn_template
ldap.dn.lookup: LDAPAuthenticator.lookup_dn
ldap.dn.search.filter: LDAPAuthenticator.lookup_dn_search_filter
ldap.dn.search.user: LDAPAuthenticator.lookup_dn_search_user
ldap.dn.search.password: LDAPAuthenticator.lookup_dn_search_password
ldap.dn.user.dnAttribute: LDAPAuthenticator.lookup_dn_user_dn_attribute
ldap.dn.user.escape: LDAPAuthenticator.escape_userdn
ldap.dn.user.validRegex: LDAPAuthenticator.valid_username_regex
ldap.dn.user.searchBase: LDAPAuthenticator.user_search_base
ldap.dn.user.attribute: LDAPAuthenticator.user_attribute
ldap.dn.user.useLookupName: LDAPAuthenticator.use_lookup_dn_username
{{- end }}

{{- /* Uses the map above, taking a keys, returning a value. */}}
{{- define "jupyterhub.authDep.remapOldToNew.single" }}
    {{- $map := include "jupyterhub.authDep.remapOldToNew.map" . | fromYaml }}
    {{- index $map . }}
{{- end }}


{{- /*
    Recursively flattens a passed dict structure, outputs the result
    in a passed dict which is assumed to be empty.
*/}}
{{- define "jupyterhub.flattenDict" }}
    {{- $out := index . 0 }}
    {{- $dict := index . 1 }}

    {{- $label := "" }}
    {{- if eq (len .) 3 }}
        {{- $label = index . 2 }}
    {{- end }}

    {{- range $key, $val := $dict }}
        {{- $sublabel := list $label $key | join "." | trimPrefix "." }}
        {{- if kindOf $val | eq "map" }}
            {{- include "jupyterhub.flattenDict" (list $out $val $sublabel) }}
        {{- else }}
            {{- $_ := set $out $sublabel $val }}
        {{- end }}
    {{- end }}
{{- end }}

{{- /*
    Remaps Recursively flattens a passed dict structure, outputs the result
    in a passed dict which is assumed to be empty.
*/}}
{{- define "jupyterhub.authDep.remapOldToNew.mappable" -}}
    {{- $c := index . 0 }}
    {{- $safe := index . 1 }}
    {{- range $key, $val := $c }}
        {{- if not $safe }}
            {{- $val = "***" }}
        {{- end }}
        {{- $_ := unset $c $key }}
        {{- $class_dot_new_key := include "jupyterhub.authDep.remapOldToNew.single" $key }}

        {{- /* Manage unrecognized config */}}
        {{- if eq $class_dot_new_key "<no value>" }}
            {{- if not (hasKey $c "WarningUnrecognizedConfig") }}
                {{- $_ := set $c "WarningUnrecognizedConfig" dict }}
            {{- end }}
            {{- $_ := set (index $c "WarningUnrecognizedConfig") $key $val }}

        {{- else }}
            {{- /* Config value transformations if needed */}}
            {{- if eq $key "state.cryptoKey" }}
                {{- $val = list $val }}
            {{- end }}

            {{- /* De-flatten the "ClassName.config_name" like strings */}}
            {{- $class := splitList "." $class_dot_new_key | first }}
            {{- $new_key := splitList "." $class_dot_new_key | last }}
            {{- if not (hasKey $c $class) }}
            {{- $_ := set $c $class dict }}
            {{- end }}
            {{- $_ := set (index $c $class) $new_key $val }}
        {{- end }}
    {{- end }}
{{- end }}

{{- define "jupyterhub.authDep.remapOldToNew" -}}
    {{- $c := dict }}
    {{- $result := (dict "hub" (dict "config" $c)) }}
    {{- /*
        Flattens the config in .Values.auth to a format of
        "keyX.keyY...": "value". Writes output to $c.
    */}}
    {{- include "jupyterhub.flattenDict" (list $c (omit .Values.auth "type" "custom")) }}

    {{- /*
        Transform the flattened config using a dictionary
        representing the old z2jh config, output the result
        in $c.
    */}}
    {{- include "jupyterhub.authDep.remapOldToNew.mappable" (list $c .Values.global.safeToShowValues) }}

    {{- $class_old_config_key := .Values.auth.type | default "" }}  {{- /* ldap                                - github */}}
    {{- $class_new_entrypoint := "" }}                              {{- /* ldapauthenticator.LDAPAuthenticator - github */}}
    {{- $class_new_config_key := "" }}                              {{- /* LDAPAuthenticator                   - GitHubOAuthenticator */}}

    {{- /* SET $class_new_entrypoint, $class_new_config_key */}}
    {{- if eq $class_old_config_key "custom" }}
        {{- $class_new_entrypoint = .Values.auth.custom.className | default "custom.className wasn't configured!" }}
        {{- $class_new_config_key = $class_new_entrypoint | splitList "." | last }}
        {{- /* UPDATE c dict explicitly with auth.custom.config */}}
        {{- if .Values.auth.custom.config }}
            {{- $custom_config := merge (dict) .Values.auth.custom.config }}
            {{- if not .Values.global.safeToShowValues }}
                {{- range $key, $val := $custom_config }}
                    {{- $_ := set $custom_config $key "***" }}
                {{- end }}
            {{- end }}
            {{- $_ := set $c $class_new_config_key $custom_config }}
        {{- end }}
    {{- else }}
        {{- $class_new_entrypoint = include "jupyterhub.authDep.classKeyToLong" $class_old_config_key }}
    {{- end }}

    {{- /* UPDATE c dict authenticator_class */}}
    {{- if ne $class_new_entrypoint "<no value>" }}
        {{- $_ := merge $c (dict "JupyterHub" (dict "authenticator_class" $class_new_entrypoint)) }}
    {{- end }}

{{- /* Output a sensible error message */}}

The JupyterHub Helm chart's auth config has been reworked and requires changes.

The new way to configure authentication in chart version 0.11.0+ is printed
below for your convenience. The values are not shown by default to ensure no
secrets are exposed, run helm upgrade with --set global.safeToShowValues=true
to show them.

{{ $result | toYaml }}

For more details, please see the updated auth config documentation at:
https://zero-to-jupyterhub.readthedocs.io/en/latest/administrator/authentication.html
{{- end }}
