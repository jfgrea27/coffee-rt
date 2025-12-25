{{/*
Expand the name of the chart.
*/}}
{{- define "flink-job.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "flink-job.fullname" -}}
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
{{- define "flink-job.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "flink-job.labels" -}}
helm.sh/chart: {{ include "flink-job.chart" . }}
{{ include "flink-job.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "flink-job.selectorLabels" -}}
app.kubernetes.io/name: {{ include "flink-job.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Flink JobManager host
*/}}
{{- define "flink-job.jobmanagerHost" -}}
{{- if .Values.flink.jobmanagerHost }}
{{- .Values.flink.jobmanagerHost }}
{{- else }}
{{- printf "%s-flink-jobmanager" .Release.Name }}
{{- end }}
{{- end }}

{{/*
Kafka bootstrap servers
*/}}
{{- define "flink-job.kafkaBootstrapServers" -}}
{{- if .Values.kafka.bootstrapServers }}
{{- .Values.kafka.bootstrapServers }}
{{- else }}
{{- printf "%s-kafka:9092" .Release.Name }}
{{- end }}
{{- end }}

{{/*
PostgreSQL host
*/}}
{{- define "flink-job.postgresHost" -}}
{{- if .Values.database.host }}
{{- .Values.database.host }}
{{- else }}
{{- printf "%s-postgresql" .Release.Name }}
{{- end }}
{{- end }}

{{/*
Redis host
*/}}
{{- define "flink-job.redisHost" -}}
{{- if .Values.redis.host }}
{{- .Values.redis.host }}
{{- else }}
{{- printf "%s-redis-master" .Release.Name }}
{{- end }}
{{- end }}

{{/*
DB Secret name - defaults to postgresql subchart secret name
*/}}
{{- define "flink-job.dbSecretName" -}}
{{- if .Values.database.secretName }}
{{- .Values.database.secretName }}
{{- else }}
{{- printf "%s-postgresql" .Release.Name }}
{{- end }}
{{- end }}
