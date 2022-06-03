{{- define "jupyterhub.userNodeAffinityRequired" -}}
{{- if eq .Values.scheduling.userPods.nodeAffinity.matchNodePurpose "require" -}}
- matchExpressions:
  - key: hub.jupyter.org/node-purpose
    operator: In
    values: [user]
{{- end }}
{{- with .Values.singleuser.extraNodeAffinity.required }}
{{- . | toYaml | nindent 0 }}
{{- end }}
{{- end }}

{{- define "jupyterhub.userNodeAffinityPreferred" -}}
{{- if eq .Values.scheduling.userPods.nodeAffinity.matchNodePurpose "prefer" -}}
- weight: 100
  preference:
    matchExpressions:
      - key: hub.jupyter.org/node-purpose
        operator: In
        values: [user]
{{- end }}
{{- with .Values.singleuser.extraNodeAffinity.preferred }}
{{- . | toYaml | nindent 0 }}
{{- end }}
{{- end }}

{{- define "jupyterhub.userPodAffinityRequired" -}}
{{- with .Values.singleuser.extraPodAffinity.required -}}
{{ . | toYaml }}
{{- end }}
{{- end }}

{{- define "jupyterhub.userPodAffinityPreferred" -}}
{{- with .Values.singleuser.extraPodAffinity.preferred -}}
{{ . | toYaml }}
{{- end }}
{{- end }}

{{- define "jupyterhub.userPodAntiAffinityRequired" -}}
{{- with .Values.singleuser.extraPodAntiAffinity.required -}}
{{ . | toYaml }}
{{- end }}
{{- end }}

{{- define "jupyterhub.userPodAntiAffinityPreferred" -}}
{{- with .Values.singleuser.extraPodAntiAffinity.preferred -}}
{{ . | toYaml }}
{{- end }}
{{- end }}



{{- /*
  jupyterhub.userAffinity:
    It is used by user-placeholder to set the same affinity on them as the
    spawned user pods spawned by kubespawner.
*/}}
{{- define "jupyterhub.userAffinity" -}}

{{- $dummy := set . "nodeAffinityRequired" (include "jupyterhub.userNodeAffinityRequired" .) -}}
{{- $dummy := set . "podAffinityRequired" (include "jupyterhub.userPodAffinityRequired" .) -}}
{{- $dummy := set . "podAntiAffinityRequired" (include "jupyterhub.userPodAntiAffinityRequired" .) -}}
{{- $dummy := set . "nodeAffinityPreferred" (include "jupyterhub.userNodeAffinityPreferred" .) -}}
{{- $dummy := set . "podAffinityPreferred" (include "jupyterhub.userPodAffinityPreferred" .) -}}
{{- $dummy := set . "podAntiAffinityPreferred" (include "jupyterhub.userPodAntiAffinityPreferred" .) -}}
{{- $dummy := set . "hasNodeAffinity" (or .nodeAffinityRequired .nodeAffinityPreferred) -}}
{{- $dummy := set . "hasPodAffinity" (or .podAffinityRequired .podAffinityPreferred) -}}
{{- $dummy := set . "hasPodAntiAffinity" (or .podAntiAffinityRequired .podAntiAffinityPreferred) -}}

{{- if .hasNodeAffinity -}}
nodeAffinity:
  {{- if .nodeAffinityRequired }}
  requiredDuringSchedulingIgnoredDuringExecution:
    nodeSelectorTerms:
      {{- .nodeAffinityRequired | nindent 6 }}
  {{- end }}

  {{- if .nodeAffinityPreferred }}
  preferredDuringSchedulingIgnoredDuringExecution:
    {{- .nodeAffinityPreferred | nindent 4 }}
  {{- end }}
{{- end }}

{{- if .hasPodAffinity }}
podAffinity:
  {{- if .podAffinityRequired }}
  requiredDuringSchedulingIgnoredDuringExecution:
    {{- .podAffinityRequired | nindent 4 }}
  {{- end }}

  {{- if .podAffinityPreferred }}
  preferredDuringSchedulingIgnoredDuringExecution:
    {{- .podAffinityPreferred | nindent 4 }}
  {{- end }}
{{- end }}

{{- if .hasPodAntiAffinity }}
podAntiAffinity:
  {{- if .podAntiAffinityRequired }}
  requiredDuringSchedulingIgnoredDuringExecution:
    {{- .podAntiAffinityRequired | nindent 4 }}
  {{- end }}

  {{- if .podAntiAffinityPreferred }}
  preferredDuringSchedulingIgnoredDuringExecution:
    {{- .podAntiAffinityPreferred | nindent 4 }}
  {{- end }}
{{- end }}

{{- end }}



{{- define "jupyterhub.coreAffinity" -}}
{{- $require := eq .Values.scheduling.corePods.nodeAffinity.matchNodePurpose "require" -}}
{{- $prefer := eq .Values.scheduling.corePods.nodeAffinity.matchNodePurpose "prefer" -}}
{{- if or $require $prefer -}}
affinity:
  nodeAffinity:
    {{- if $require }}
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
          - key: hub.jupyter.org/node-purpose
            operator: In
            values: [core]
    {{- end }}
    {{- if $prefer }}
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions:
            - key: hub.jupyter.org/node-purpose
              operator: In
              values: [core]
    {{- end }}
{{- end }}
{{- end }}
