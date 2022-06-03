{{- /*
    This file contains logic to lookup already
    generated passwords or generate a new.

    proxy.secretToken       / hub.config.ConfigurableHTTPProxy.auth_token
    hub.cookieSecret        / hub.config.JupyterHub.cookie_secret
    auth.state.cryptoKey*   / hub.config.CryptKeeper.keys

    *Note that the entire auth section is deprecated and users
    are forced through "fail" in NOTES.txt to migrate to hub.config.

    Note that lookup logic returns falsy value when run with
    `helm diff upgrade`, so it is a bit troublesome to test.
*/}}

{{- /*
    Returns given number of random Hex characters.

    - randNumeric 4 | atoi generates a random number in [0, 10^4)
      This is a range range evenly divisble by 16, but even if off by one,
      that last partial interval offsetting randomness is only 1 part in 625.
    - mod N 16 maps to the range 0-15
    - printf "%x" represents a single number 0-15 as a single hex character
*/}}
{{- define "jupyterhub.randHex" -}}
    {{- $result := "" }}
    {{- range $i := until . }}
        {{- $rand_hex_char := mod (randNumeric 4 | atoi) 16 | printf "%x" }}
        {{- $result = print $result $rand_hex_char }}
    {{- end }}
    {{- $result }}
{{- end }}

{{- define "jupyterhub.hub.config.ConfigurableHTTPProxy.auth_token" -}}
    {{- if (.Values.hub.config | dig "ConfigurableHTTPProxy" "auth_token" "") }}
        {{- .Values.hub.config.ConfigurableHTTPProxy.auth_token }}
    {{- else if .Values.proxy.secretToken }}
        {{- .Values.proxy.secretToken }}
    {{- else }}
        {{- $k8s_state := lookup "v1" "Secret" .Release.Namespace (include "jupyterhub.hub.fullname" .) | default (dict "data" (dict)) }}
        {{- if hasKey $k8s_state.data "hub.config.ConfigurableHTTPProxy.auth_token" }}
            {{- index $k8s_state.data "hub.config.ConfigurableHTTPProxy.auth_token" | b64dec }}
        {{- else }}
            {{- randAlphaNum 64 }}
        {{- end }}
    {{- end }}
{{- end }}

{{- define "jupyterhub.hub.config.JupyterHub.cookie_secret" -}}
    {{- if (.Values.hub.config | dig "JupyterHub" "cookie_secret" "") }}
        {{- .Values.hub.config.JupyterHub.cookie_secret }}
    {{- else if .Values.hub.cookieSecret }}
        {{- .Values.hub.cookieSecret }}
    {{- else }}
        {{- $k8s_state := lookup "v1" "Secret" .Release.Namespace (include "jupyterhub.hub.fullname" .) | default (dict "data" (dict)) }}
        {{- if hasKey $k8s_state.data "hub.config.JupyterHub.cookie_secret" }}
            {{- index $k8s_state.data "hub.config.JupyterHub.cookie_secret" | b64dec }}
        {{- else }}
            {{- include "jupyterhub.randHex" 64 }}
        {{- end }}
    {{- end }}
{{- end }}

{{- define "jupyterhub.hub.config.CryptKeeper.keys" -}}
    {{- if (.Values.hub.config | dig "CryptKeeper" "keys" "") }}
        {{- .Values.hub.config.CryptKeeper.keys | join ";" }}
    {{- else }}
        {{- $k8s_state := lookup "v1" "Secret" .Release.Namespace (include "jupyterhub.hub.fullname" .) | default (dict "data" (dict)) }}
        {{- if hasKey $k8s_state.data "hub.config.CryptKeeper.keys" }}
            {{- index $k8s_state.data "hub.config.CryptKeeper.keys" | b64dec }}
        {{- else }}
            {{- include "jupyterhub.randHex" 64 }}
        {{- end }}
    {{- end }}
{{- end }}

{{- define "jupyterhub.hub.services.get_api_token" -}}
    {{- $_ := index . 0 }}
    {{- $service_key := index . 1 }}
    {{- $explicitly_set_api_token := or ($_.Values.hub.services | dig $service_key "api_token" "") ($_.Values.hub.services | dig $service_key "apiToken" "") }}
    {{- if $explicitly_set_api_token }}
        {{- $explicitly_set_api_token }}
    {{- else }}
        {{- $k8s_state := lookup "v1" "Secret" $_.Release.Namespace (include "jupyterhub.hub.fullname" $_) | default (dict "data" (dict)) }}
        {{- $k8s_secret_key := print "hub.services." $service_key ".apiToken" }}
        {{- if hasKey $k8s_state.data $k8s_secret_key }}
            {{- index $k8s_state.data $k8s_secret_key | b64dec }}
        {{- else }}
            {{- include "jupyterhub.randHex" 64 }}
        {{- end }}
    {{- end }}
{{- end }}
