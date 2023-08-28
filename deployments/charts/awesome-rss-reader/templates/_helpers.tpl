{{- define "awesome-rss-reader.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "awesome-rss-reader.podname" -}}
{{- printf "%s-%s" .Release.Name .Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "awesome-rss-reader.selectorLabels" -}}
{{ include "awesome-rss-reader.releaseLabels" . }}
{{- end }}

{{- define "awesome-rss-reader.releaseLabels" -}}
app.kubernetes.io/name: {{ include "awesome-rss-reader.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "awesome-rss-reader.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "awesome-rss-reader.labels" -}}
helm.sh/chart: {{ include "awesome-rss-reader.chart" . }}
{{ include "awesome-rss-reader.releaseLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
