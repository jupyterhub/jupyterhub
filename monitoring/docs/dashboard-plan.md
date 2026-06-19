# Dashboard Plan

This document defines the first SAIEP dashboards for the monitoring module.
The plan is centered on JupyterHub first, while leaving room for future Loki
log panels and additional platform services.

## 1. System Health Dashboard

### Purpose

This dashboard gives operators a quick answer to one question: is JupyterHub
healthy right now?

### Panels

- Service availability
- CPU usage trend
- Memory usage trend
- Request latency percentiles
- Active users
- Running servers
- Spawn duration histogram

### Metrics displayed

- `up`
- `process_cpu_seconds_total`
- `process_resident_memory_bytes`
- `jupyterhub_active_users`
- `jupyterhub_running_servers`
- `jupyterhub_request_duration_seconds`
- `jupyterhub_server_spawn_duration_seconds`

### Associated alerts

- `ServiceDown`
- `HighCPUUsage`
- `HighMemoryUsage`

### Use cases

- detect service outages early;
- understand whether the Hub is overloaded;
- identify slow requests or slow spawn behavior;
- support day-to-day operations.

## 2. Security Events Dashboard

### Purpose

This dashboard focuses on authentication and security-related activity.
It helps operators spot suspicious behavior or degraded authentication flows.

### Panels

- Failed authentication attempts
- Login duration by status
- CSP violation reports
- Proxy route add failures
- Login request volume
- Future Loki-based security event panels

### Metrics displayed

- `jupyterhub_login_duration_seconds`
- `jupyterhub_csp_reports`
- `jupyterhub_proxy_add_duration_seconds`
- `jupyterhub_request_duration_seconds`
- Loki log queries for auth failures and access anomalies, when Promtail is in place

### Associated alerts

- `ServiceDown`
- Future auth anomaly alerting based on failed login spikes
- Future security log alerts from Loki

### Use cases

- investigate repeated login failures;
- track security policy violations;
- observe route-provisioning failures around user sessions;
- correlate metrics with logs during incident response.

## 3. Capacity Planning Dashboard

### Purpose

This dashboard helps the team size the platform correctly and plan resource
growth before users feel pain.

### Panels

- Total users
- Active users over time
- Running servers over time
- Spawn latency percentiles
- Request latency percentiles
- CPU trend
- Memory trend
- Disk headroom

### Metrics displayed

- `jupyterhub_total_users`
- `jupyterhub_active_users`
- `jupyterhub_running_servers`
- `jupyterhub_server_spawn_duration_seconds`
- `jupyterhub_request_duration_seconds`
- `process_cpu_seconds_total`
- `process_resident_memory_bytes`
- `node_filesystem_avail_bytes`
- `node_filesystem_size_bytes`

### Associated alerts

- `HighCPUUsage`
- `HighMemoryUsage`
- `LowDiskSpace`
- Future spawn-latency alert if spawn times drift upward

### Use cases

- estimate when to increase Hub or node resources;
- identify pressure points before they become outages;
- justify infrastructure sizing decisions;
- follow usage trends across releases and semesters.

## Sprint 1 delivery note

The first iteration of the dashboards should stay focused on JupyterHub and
basic platform signals. Loki, Promtail, and any service-specific dashboards can
be added once other teams expose their endpoints and logging requirements.
