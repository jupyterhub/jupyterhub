# List of Prometheus Metrics

```{versionchanged} 6.0
`jupyterhub_server_spawn_duration_seconds` adds a `reason` label
and splits the previous `status=failure` into `status=error` for unhandled errors and `status=failure` for rejected spawns, such as those which raise {class}`.SpawnException`.
```

```{include} ../includes/metrics_table.md
```
