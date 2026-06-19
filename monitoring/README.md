# Monitoring

This directory contains the observability stack for SAIEP.
Its goal is to give the platform team a clear view of service health,
performance, capacity, and security signals, even while other modules are
still under development.

## Monitoring objective

The monitoring module is responsible for:

- tracking JupyterHub availability and performance;
- collecting platform-level resource signals;
- defining actionable alerts for operators;
- preparing the foundation for logs, dashboards, and future observability growth.

## Monitoring architecture

The Sprint 1 architecture is intentionally simple and independent:

1. JupyterHub exposes metrics on `/hub/metrics`.
2. Prometheus scrapes those metrics every 30 seconds.
3. Prometheus stores time-series data and evaluates alert rules.
4. Alertmanager routes notifications when alert conditions are met.
5. Grafana consumes Prometheus data to build operational dashboards.
6. Loki and Promtail will later add centralized log collection and log search.

## Integration with JupyterHub

JupyterHub is the first and most stable observability target in SAIEP.
The repository already documents the metrics endpoint and the scrape interval,
and the monitoring manifests in this folder are aligned with that behavior.

Current monitoring assets:

- `monitoring/prometheus/prometheus.yml.example`
- `monitoring/prometheus/servicemonitor.yaml`
- `monitoring/prometheus/alert-rules.yaml`

## Role of Prometheus

Prometheus is the metrics engine of the platform.
It scrapes JupyterHub, keeps historical data, and evaluates alert expressions.
It is also the main data source for future Grafana dashboards.

## Role of Grafana

Grafana is the visualization layer.
It will be used to:

- monitor JupyterHub health in real time;
- inspect CPU, memory, traffic, and spawn patterns;
- support capacity planning;
- correlate service health with operational events.

## Role of Alertmanager

Alertmanager is the notification and routing layer.
It groups alerts, applies deduplication, and forwards critical signals to the
appropriate notification channels.
It becomes the bridge between raw Prometheus rule evaluation and operational action.

## Future Loki and Promtail integration

Logs are the next observability layer for SAIEP.

- Promtail will collect logs from Kubernetes workloads and nodes.
- Loki will index and store those logs efficiently.
- Grafana will combine metrics from Prometheus and logs from Loki in the same
  operational view.

This will make it possible to investigate authentication issues, proxy errors,
spawn failures, and security events without leaving the monitoring stack.

## Sprint 1 directory structure

```text
monitoring/
├── prometheus/
├── grafana/
├── alertmanager/
├── loki/
├── promtail/
└── docs/
```