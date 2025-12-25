{{/*
Expand the name of the chart.
*/}}
{{- define "flink.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "flink.fullname" -}}
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
{{- define "flink.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "flink.labels" -}}
helm.sh/chart: {{ include "flink.chart" . }}
{{ include "flink.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "flink.selectorLabels" -}}
app.kubernetes.io/name: {{ include "flink.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
JobManager selector labels
*/}}
{{- define "flink.jobmanager.selectorLabels" -}}
{{ include "flink.selectorLabels" . }}
app.kubernetes.io/component: jobmanager
{{- end }}

{{/*
TaskManager selector labels
*/}}
{{- define "flink.taskmanager.selectorLabels" -}}
{{ include "flink.selectorLabels" . }}
app.kubernetes.io/component: taskmanager
{{- end }}


{{/*
Database host - defaults to postgresql subchart service name
*/}}
{{- define "flink.databaseHost" -}}
{{- if .Values.database.host }}
{{- .Values.database.host }}
{{- else }}
{{- printf "%s-postgresql" .Release.Name }}
{{- end }}
{{- end }}

{{/*
Redis host - defaults to redis subchart service name
*/}}
{{- define "flink.redisHost" -}}
{{- if .Values.redis.host }}
{{- .Values.redis.host }}
{{- else }}
{{- printf "%s-redis-master" .Release.Name }}
{{- end }}
{{- end }}

{{/*
Kafka bootstrap servers - defaults to kafka subchart service name
*/}}
{{- define "flink.kafkaBootstrapServers" -}}
{{- if .Values.kafka.bootstrapServers }}
{{- .Values.kafka.bootstrapServers }}
{{- else }}
{{- printf "%s-kafka:9092" .Release.Name }}
{{- end }}
{{- end }}
