{{- /*
Returns an image-puller daemonset. Two daemonsets will be created like this.
- hook-image-puller: for pre helm upgrade image pulling (lives temporarily)
- continuous-image-puller: for newly added nodes image pulling
*/}}
{{- define "jupyterhub.imagePuller.daemonset" -}}
apiVersion: apps/v1
kind: DaemonSet
metadata:
  {{- if .hook }}
  name: {{ include "jupyterhub.hook-image-puller.fullname" . }}
  {{- else }}
  name: {{ include "jupyterhub.continuous-image-puller.fullname" . }}
  {{- end }}
  labels:
    {{- include "jupyterhub.labels" . | nindent 4 }}
    {{- if .hook }}
    hub.jupyter.org/deletable: "true"
    {{- end }}
  {{- if .hook }}
  annotations:
    {{- /*
    Allows the daemonset to be deleted when the image-awaiter job is completed.
    */}}
    "helm.sh/hook": pre-install,pre-upgrade
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
    "helm.sh/hook-weight": "-10"
  {{- end }}
spec:
  selector:
    matchLabels:
      {{- include "jupyterhub.matchLabels" . | nindent 6 }}
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 100%
  template:
    metadata:
      labels:
        {{- include "jupyterhub.matchLabels" . | nindent 8 }}
      {{- with .Values.prePuller.annotations }}
      annotations:
        {{- . | toYaml | nindent 8 }}
      {{- end }}
    spec:
      {{- /*
        continuous-image-puller pods are made evictable to save on the k8s pods
        per node limit all k8s clusters have.
      */}}
      {{- if and (not .hook) .Values.scheduling.podPriority.enabled }}
      priorityClassName: {{ include "jupyterhub.user-placeholder-priority.fullname" . }}
      {{- end }}
      nodeSelector: {{ toJson .Values.singleuser.nodeSelector }}
      {{- with concat .Values.scheduling.userPods.tolerations .Values.singleuser.extraTolerations .Values.prePuller.extraTolerations }}
      tolerations:
        {{- . | toYaml | nindent 8 }}
      {{- end }}
      {{- if include "jupyterhub.userNodeAffinityRequired" . }}
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              {{- include "jupyterhub.userNodeAffinityRequired" . | nindent 14 }}
      {{- end }}
      terminationGracePeriodSeconds: 0
      automountServiceAccountToken: false
      {{- with include "jupyterhub.imagePullSecrets" (dict "root" . "image" .Values.singleuser.image) }}
      imagePullSecrets: {{ . }}
      {{- end }}
      initContainers:
        {{- /* --- Conditionally pull an image all user pods will use in an initContainer --- */}}
        {{- $blockWithIptables := hasKey .Values.singleuser.cloudMetadata "enabled" | ternary (not .Values.singleuser.cloudMetadata.enabled) .Values.singleuser.cloudMetadata.blockWithIptables }}
        {{- if $blockWithIptables }}
        - name: image-pull-metadata-block
          image: {{ .Values.singleuser.networkTools.image.name }}:{{ .Values.singleuser.networkTools.image.tag }}
          {{- with .Values.singleuser.networkTools.image.pullPolicy }}
          imagePullPolicy: {{ . }}
          {{- end }}
          command:
            - /bin/sh
            - -c
            - echo "Pulling complete"
          {{- with .Values.prePuller.resources }}
          resources:
            {{- . | toYaml | nindent 12 }}
          {{- end }}
          {{- with .Values.prePuller.containerSecurityContext }}
          securityContext:
            {{- . | toYaml | nindent 12 }}
          {{- end }}
        {{- end }}

        {{- /* --- Pull default image --- */}}
        - name: image-pull-singleuser
          image: {{ .Values.singleuser.image.name }}:{{ .Values.singleuser.image.tag }}
          command:
            - /bin/sh
            - -c
            - echo "Pulling complete"
          {{- with .Values.prePuller.resources }}
          resources:
            {{- . | toYaml | nindent 12 }}
          {{- end }}
          {{- with .Values.prePuller.containerSecurityContext }}
          securityContext:
            {{- . | toYaml | nindent 12 }}
          {{- end }}

        {{- /* --- Pull extra containers' images --- */}}
        {{- range $k, $container := concat .Values.singleuser.initContainers .Values.singleuser.extraContainers }}
        - name: image-pull-singleuser-init-and-extra-containers-{{ $k }}
          image: {{ $container.image }}
          command:
            - /bin/sh
            - -c
            - echo "Pulling complete"
          {{- with $.Values.prePuller.resources }}
          resources:
            {{- . | toYaml | nindent 12 }}
          {{- end }}
          {{- with $.Values.prePuller.containerSecurityContext }}
          securityContext:
            {{- . | toYaml | nindent 12 }}
          {{- end }}
        {{- end }}

        {{- /* --- Conditionally pull profileList images --- */}}
        {{- if .Values.prePuller.pullProfileListImages }}
        {{- range $k, $container := .Values.singleuser.profileList }}
        {{- if $container.kubespawner_override }}
        {{- if $container.kubespawner_override.image }}
        - name: image-pull-singleuser-profilelist-{{ $k }}
          image: {{ $container.kubespawner_override.image }}
          command:
            - /bin/sh
            - -c
            - echo "Pulling complete"
          {{- with $.Values.prePuller.resources }}
          resources:
            {{- . | toYaml | nindent 12 }}
          {{- end }}
          {{- with $.Values.prePuller.containerSecurityContext }}
          securityContext:
            {{- . | toYaml | nindent 12 }}
          {{- end }}
        {{- end }}
        {{- end }}
        {{- end }}
        {{- end }}

        {{- /* --- Pull extra images --- */}}
        {{- range $k, $v := .Values.prePuller.extraImages }}
        - name: image-pull-{{ $k }}
          image: {{ $v.name }}:{{ $v.tag }}
          command:
            - /bin/sh
            - -c
            - echo "Pulling complete"
          {{- with $.Values.prePuller.resources }}
          resources:
            {{- . | toYaml | nindent 12 }}
          {{- end }}
          {{- with $.Values.prePuller.containerSecurityContext }}
          securityContext:
            {{- . | toYaml | nindent 12 }}
          {{- end }}
        {{- end }}
      containers:
        - name: pause
          image: {{ .Values.prePuller.pause.image.name }}:{{ .Values.prePuller.pause.image.tag }}
          {{- with .Values.prePuller.resources }}
          resources:
            {{- . | toYaml | nindent 12 }}
          {{- end }}
          {{- with .Values.prePuller.pause.containerSecurityContext }}
          securityContext:
            {{- . | toYaml | nindent 12 }}
          {{- end }}
{{- end }}


{{- /*
    Returns a rendered k8s DaemonSet resource: continuous-image-puller
*/}}
{{- define "jupyterhub.imagePuller.daemonset.continuous" -}}
    {{- $_ := merge (dict "hook" false "componentPrefix" "continuous-") . }}
    {{- include "jupyterhub.imagePuller.daemonset" $_ }}
{{- end }}


{{- /*
    Returns a rendered k8s DaemonSet resource: hook-image-puller
*/}}
{{- define "jupyterhub.imagePuller.daemonset.hook" -}}
    {{- $_ := merge (dict "hook" true "componentPrefix" "hook-") . }}
    {{- include "jupyterhub.imagePuller.daemonset" $_ }}
{{- end }}


{{- /*
    Returns a checksum of the rendered k8s DaemonSet resource: hook-image-puller

    This checksum is used when prePuller.hook.pullOnlyOnChanges=true to decide if
    it is worth creating the hook-image-puller associated resources.
*/}}
{{- define "jupyterhub.imagePuller.daemonset.hook.checksum" -}}
    {{- /*
        We pin componentLabel and Chart.Version as doing so can pin labels
        of no importance if they would change. Chart.Name is also pinned as
        a harmless technical workaround when we compute the checksum.
    */}}
    {{- $_ := merge (dict "componentLabel" "pinned" "Chart" (dict "Name" "jupyterhub" "Version" "pinned")) . -}}
    {{- $yaml := include "jupyterhub.imagePuller.daemonset.hook" $_ }}
    {{- $yaml | sha256sum }}
{{- end }}


{{- /*
    Returns a truthy string or a blank string depending on if the
    hook-image-puller should be installed. The truthy strings are comments
    that summarize the state that led to returning a truthy string.

    - prePuller.hook.enabled must be true
    - if prePuller.hook.pullOnlyOnChanges is true, the checksum of the
      hook-image-puller daemonset must differ since last upgrade
*/}}
{{- define "jupyterhub.imagePuller.daemonset.hook.install" -}}
    {{- if .Values.prePuller.hook.enabled }}
        {{- if .Values.prePuller.hook.pullOnlyOnChanges }}
            {{- $new_checksum := include "jupyterhub.imagePuller.daemonset.hook.checksum" . }}
            {{- $k8s_state := lookup "v1" "ConfigMap" .Release.Namespace (include "jupyterhub.hub.fullname" .) | default (dict "data" (dict)) }}
            {{- $old_checksum := index $k8s_state.data "checksum_hook-image-puller" | default "" }}
            {{- if ne $new_checksum $old_checksum -}}
# prePuller.hook.enabled={{ .Values.prePuller.hook.enabled }}
# prePuller.hook.pullOnlyOnChanges={{ .Values.prePuller.hook.pullOnlyOnChanges }}
# post-upgrade checksum != pre-upgrade checksum (of the hook-image-puller DaemonSet)
# "{{ $new_checksum }}" != "{{ $old_checksum}}"
            {{- end }}
        {{- else -}}
# prePuller.hook.enabled={{ .Values.prePuller.hook.enabled }}
# prePuller.hook.pullOnlyOnChanges={{ .Values.prePuller.hook.pullOnlyOnChanges }}
        {{- end }}
    {{- end }}
{{- end }}
