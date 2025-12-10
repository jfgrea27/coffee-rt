{{/*
Expand the name of the chart.
*/}}
{{- define "coffee-rt.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "coffee-rt.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "coffee-rt.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "coffee-rt.labels" -}}
helm.sh/chart: {{ include "coffee-rt.chart" . }}
{{ include "coffee-rt.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "coffee-rt.selectorLabels" -}}
app.kubernetes.io/name: {{ include "coffee-rt.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Database host - defaults to postgresql subchart service name
*/}}
{{- define "coffee-rt.databaseHost" -}}
{{- if .Values.database.host }}
{{- .Values.database.host }}
{{- else }}
{{- printf "%s-postgresql" .Release.Name }}
{{- end }}
{{- end }}

{{/*
Redis host - defaults to redis subchart service name
*/}}
{{- define "coffee-rt.redisHost" -}}
{{- if .Values.redisConfig.host }}
{{- .Values.redisConfig.host }}
{{- else }}
{{- printf "%s-redis-master" .Release.Name }}
{{- end }}
{{- end }}

{{/*
Database secret name
*/}}
{{- define "coffee-rt.databaseSecretName" -}}
{{- if .Values.database.existingSecret }}
{{- .Values.database.existingSecret }}
{{- else }}
{{- printf "%s-db-secret" .Release.Name }}
{{- end }}
{{- end }}
