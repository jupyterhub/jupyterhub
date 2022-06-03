{{- /*
  ## About
  This file contains helpers to systematically name, label and select Kubernetes
  objects we define in the .yaml template files.


  ## How helpers work
  Helm helper functions is a good way to avoid repeating something. They will
  generate some output based on one single dictionary of input that we call the
  helpers scope. When you are in helm, you access your current scope with a
  single a single punctuation (.).

  When you ask a helper to render its content, one often forward the current
  scope to the helper in order to allow it to access .Release.Name,
  .Values.rbac.enabled and similar values.

  #### Example - Passing the current scope
  {{ include "jupyterhub.commonLabels" . }}

  It would be possible to pass something specific instead of the current scope
  (.), but that would make .Release.Name etc. inaccessible by the helper which
  is something we aim to avoid.

  #### Example - Passing a new scope
  {{ include "demo.bananaPancakes" (dict "pancakes" 5 "bananas" 3) }}

  To let a helper access the current scope along with additional values we have
  opted to create dictionary containing additional values that is then populated
  with additional values from the current scope through a the merge function.

  #### Example - Passing a new scope augmented with the old
  {{- $_ := merge (dict "appLabel" "kube-lego") . }}
  {{- include "jupyterhub.matchLabels" $_ | nindent 6 }}

  In this way, the code within the definition of `jupyterhub.matchLabels` will
  be able to access .Release.Name and .appLabel.

  NOTE:
    The ordering of merge is crucial, the latter argument is merged into the
    former. So if you would swap the order you would influence the current scope
    risking unintentional behavior. Therefore, always put the fresh unreferenced
    dictionary (dict "key1" "value1") first and the current scope (.) last.


  ## Declared helpers
  - appLabel          |
  - componentLabel    |
  - commonLabels      | uses appLabel
  - labels            | uses commonLabels
  - matchLabels       | uses labels
  - podCullerSelector | uses matchLabels


  ## Example usage
  ```yaml
  # Excerpt from proxy/autohttps/deployment.yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: {{ include "jupyterhub.autohttps.fullname" . }}
    labels:
      {{- include "jupyterhub.labels" . | nindent 4 }}
  spec:
    selector:
      matchLabels:
        {{- include "jupyterhub.matchLabels" $_ | nindent 6 }}
    template:
      metadata:
        labels:
          {{- include "jupyterhub.labels" $_ | nindent 8 }}
          hub.jupyter.org/network-access-proxy-http: "true"
  ```

  NOTE:
    The "jupyterhub.matchLabels" and "jupyterhub.labels" is passed an augmented
    scope that will influence the helpers' behavior. It get the current scope
    "." but merged with a dictionary containing extra key/value pairs. In this
    case the "." scope was merged with a small dictionary containing only one
    key/value pair "appLabel: kube-lego". It is required for kube-lego to
    function properly. It is a way to override the default app label's value.
*/}}


{{- /*
  jupyterhub.appLabel:
    Used by "jupyterhub.labels".
*/}}
{{- define "jupyterhub.appLabel" -}}
{{ .Values.nameOverride | default .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}


{{- /*
  jupyterhub.componentLabel:
    Used by "jupyterhub.labels".

    NOTE: The component label is determined by either...
    - 1: The provided scope's .componentLabel
    - 2: The template's filename if living in the root folder
    - 3: The template parent folder's name
    -  : ...and is combined with .componentPrefix and .componentSuffix
*/}}
{{- define "jupyterhub.componentLabel" -}}
{{- $file := .Template.Name | base | trimSuffix ".yaml" -}}
{{- $parent := .Template.Name | dir | base | trimPrefix "templates" -}}
{{- $component := .componentLabel | default $parent | default $file -}}
{{- $component := print (.componentPrefix | default "") $component (.componentSuffix | default "") -}}
{{ $component }}
{{- end }}


{{- /*
  jupyterhub.commonLabels:
    Foundation for "jupyterhub.labels".
    Provides labels: app, release, (chart and heritage).
*/}}
{{- define "jupyterhub.commonLabels" -}}
app: {{ .appLabel | default (include "jupyterhub.appLabel" .) }}
release: {{ .Release.Name }}
{{- if not .matchLabels }}
chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
heritage: {{ .heritageLabel | default .Release.Service }}
{{- end }}
{{- end }}


{{- /*
  jupyterhub.labels:
    Provides labels: component, app, release, (chart and heritage).
*/}}
{{- define "jupyterhub.labels" -}}
component: {{ include "jupyterhub.componentLabel" . }}
{{ include "jupyterhub.commonLabels" . }}
{{- end }}


{{- /*
  jupyterhub.matchLabels:
    Used to provide pod selection labels: component, app, release.
*/}}
{{- define "jupyterhub.matchLabels" -}}
{{- $_ := merge (dict "matchLabels" true) . -}}
{{ include "jupyterhub.labels" $_ }}
{{- end }}


{{- /*
  jupyterhub.dockerconfigjson:
    Creates a base64 encoded docker registry json blob for use in a image pull
    secret, just like the `kubectl create secret docker-registry` command does
    for the generated secrets data.dockerconfigjson field. The output is
    verified to be exactly the same even if you have a password spanning
    multiple lines as you may need to use a private GCR registry.

    - https://kubernetes.io/docs/concepts/containers/images/#specifying-imagepullsecrets-on-a-pod
*/}}
{{- define "jupyterhub.dockerconfigjson" -}}
{{ include "jupyterhub.dockerconfigjson.yaml" . | b64enc }}
{{- end }}

{{- define "jupyterhub.dockerconfigjson.yaml" -}}
{{- with .Values.imagePullSecret -}}
{
  "auths": {
    {{ .registry | default "https://index.docker.io/v1/" | quote }}: {
      "username": {{ .username | quote }},
      "password": {{ .password | quote }},
      {{- if .email }}
      "email": {{ .email | quote }},
      {{- end }}
      "auth": {{ (print .username ":" .password) | b64enc | quote }}
    }
  }
}
{{- end }}
{{- end }}

{{- /*
  jupyterhub.imagePullSecrets
    Augments passed .pullSecrets with $.Values.imagePullSecrets
*/}}
{{- define "jupyterhub.imagePullSecrets" -}}
{{- /* Populate $_.list with all relevant entries */}}
{{- $_ := dict "list" (concat .image.pullSecrets .root.Values.imagePullSecrets | uniq) }}
{{- if and .root.Values.imagePullSecret.create .root.Values.imagePullSecret.automaticReferenceInjection }}
{{- $__ := set $_ "list" (append $_.list (include "jupyterhub.image-pull-secret.fullname" .root) | uniq) }}
{{- end }}

{{- /* Decide if something should be written */}}
{{- if not (eq ($_.list | toJson) "[]") }}

{{- /* Process the $_.list where strings become dicts with a name key and the
strings become the name keys' values into $_.res */}}
{{- $_ := set $_ "res" list }}
{{- range $_.list }}
{{- if eq (typeOf .) "string" }}
{{- $__ := set $_ "res" (append $_.res (dict "name" .)) }}
{{- else }}
{{- $__ := set $_ "res" (append $_.res .) }}
{{- end }}
{{- end }}

{{- /* Write the results */}}
{{- $_.res | toJson }}

{{- end }}
{{- end }}

{{- /*
  jupyterhub.singleuser.resources:
    The resource request of a singleuser.
*/}}
{{- define "jupyterhub.singleuser.resources" -}}
{{- $r1 := .Values.singleuser.cpu.guarantee -}}
{{- $r2 := .Values.singleuser.memory.guarantee -}}
{{- $r3 := .Values.singleuser.extraResource.guarantees -}}
{{- $r := or $r1 $r2 $r3 -}}
{{- $l1 := .Values.singleuser.cpu.limit -}}
{{- $l2 := .Values.singleuser.memory.limit -}}
{{- $l3 := .Values.singleuser.extraResource.limits -}}
{{- $l := or $l1 $l2 $l3 -}}
{{- if $r -}}
requests:
  {{- if $r1 }}
  cpu: {{ .Values.singleuser.cpu.guarantee }}
  {{- end }}
  {{- if $r2 }}
  memory: {{ .Values.singleuser.memory.guarantee }}
  {{- end }}
  {{- if $r3 }}
  {{- range $key, $value := .Values.singleuser.extraResource.guarantees }}
  {{ $key | quote }}: {{ $value | quote }}
  {{- end }}
  {{- end }}
{{- end }}

{{- if $l }}
limits:
  {{- if $l1 }}
  cpu: {{ .Values.singleuser.cpu.limit }}
  {{- end }}
  {{- if $l2 }}
  memory: {{ .Values.singleuser.memory.limit }}
  {{- end }}
  {{- if $l3 }}
  {{- range $key, $value := .Values.singleuser.extraResource.limits }}
  {{ $key | quote }}: {{ $value | quote }}
  {{- end }}
  {{- end }}
{{- end }}
{{- end }}

{{- /*
  jupyterhub.extraEnv:
    Output YAML formatted EnvVar entries for use in a containers env field.
*/}}
{{- define "jupyterhub.extraEnv" -}}
{{- include "jupyterhub.extraEnv.withTrailingNewLine" . | trimSuffix "\n" }}
{{- end }}

{{- define "jupyterhub.extraEnv.withTrailingNewLine" -}}
{{- if . }}
{{- /* If extraEnv is a list, we inject it as it is. */}}
{{- if eq (typeOf .) "[]interface {}" }}
{{- . | toYaml }}

{{- /* If extraEnv is a map, we differentiate two cases: */}}
{{- else if eq (typeOf .) "map[string]interface {}" }}
{{- range $key, $value := . }}
{{- /*
    - If extraEnv.someKey has a map value, then we add the value as a YAML
      parsed list element and use the key as the name value unless its
      explicitly set.
*/}}
{{- if eq (typeOf $value) "map[string]interface {}" }}
{{- merge (dict) $value (dict "name" $key) | list | toYaml | println }}
{{- /*
    - If extraEnv.someKey has a string value, then we use the key as the
      environment variable name for the value.
*/}}
{{- else if eq (typeOf $value) "string" -}}
- name: {{ $key | quote }}
  value: {{ $value | quote | println }}
{{- else }}
{{- printf "?.extraEnv.%s had an unexpected type (%s)" $key (typeOf $value) | fail }}
{{- end }}
{{- end }} {{- /* end of range */}}
{{- end }}
{{- end }} {{- /* end of: if . */}}
{{- end }} {{- /* end of definition */}}

{{- /*
  jupyterhub.extraFiles.data:
    Renders content for a k8s Secret's data field, coming from extraFiles with
    binaryData entries.
*/}}
{{- define "jupyterhub.extraFiles.data.withNewLineSuffix" -}}
    {{- range $file_key, $file_details := . }}
        {{- include "jupyterhub.extraFiles.validate-file" (list $file_key $file_details) }}
        {{- if $file_details.binaryData }}
            {{- $file_key | quote }}: {{ $file_details.binaryData | nospace | quote }}{{ println }}
        {{- end }}
    {{- end }}
{{- end }}
{{- define "jupyterhub.extraFiles.data" -}}
    {{- include "jupyterhub.extraFiles.data.withNewLineSuffix" . | trimSuffix "\n" }}
{{- end }}

{{- /*
  jupyterhub.extraFiles.stringData:
    Renders content for a k8s Secret's stringData field, coming from extraFiles
    with either data or stringData entries.
*/}}
{{- define "jupyterhub.extraFiles.stringData.withNewLineSuffix" -}}
    {{- range $file_key, $file_details := . }}
        {{- include "jupyterhub.extraFiles.validate-file" (list $file_key $file_details) }}
        {{- $file_name := $file_details.mountPath | base }}
        {{- if $file_details.stringData }}
            {{- $file_key | quote }}: |
              {{- $file_details.stringData | trimSuffix "\n" | nindent 2 }}{{ println }}
        {{- end }}
        {{- if $file_details.data }}
            {{- $file_key | quote }}: |
              {{- if or (eq (ext $file_name) ".yaml") (eq (ext $file_name) ".yml") }}
              {{- $file_details.data | toYaml | nindent 2 }}{{ println }}
              {{- else if eq (ext $file_name) ".json" }}
              {{- $file_details.data | toJson | nindent 2 }}{{ println }}
              {{- else if eq (ext $file_name) ".toml" }}
              {{- $file_details.data | toToml | trimSuffix "\n" | nindent 2 }}{{ println }}
              {{- else }}
              {{- print "\n\nextraFiles entries with 'data' (" $file_key " > " $file_details.mountPath ") needs to have a filename extension of .yaml, .yml, .json, or .toml!" | fail }}
              {{- end }}
        {{- end }}
    {{- end }}
{{- end }}
{{- define "jupyterhub.extraFiles.stringData" -}}
    {{- include "jupyterhub.extraFiles.stringData.withNewLineSuffix" . | trimSuffix "\n" }}
{{- end }}

{{- define "jupyterhub.extraFiles.validate-file" -}}
    {{- $file_key := index . 0 }}
    {{- $file_details := index . 1 }}

    {{- /* Use of mountPath. */}}
    {{- if not ($file_details.mountPath) }}
        {{- print "\n\nextraFiles entries (" $file_key ") must contain the field 'mountPath'." | fail }}
    {{- end }}

    {{- /* Use one of stringData, binaryData, data. */}}
    {{- $field_count := 0 }}
    {{- if $file_details.data }}
        {{- $field_count = add1 $field_count }}
    {{- end }}
    {{- if $file_details.stringData }}
        {{- $field_count = add1 $field_count }}
    {{- end }}
    {{- if $file_details.binaryData }}
        {{- $field_count = add1 $field_count }}
    {{- end }}
    {{- if ne $field_count 1 }}
        {{- print "\n\nextraFiles entries (" $file_key ") must only contain one of the fields: 'data', 'stringData', and 'binaryData'." | fail }}
    {{- end }}
{{- end }}
