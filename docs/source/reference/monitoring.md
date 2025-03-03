# Monitoring

This section covers details on monitoring the state of your JupyterHub installation.

JupyterHub expose the `/metrics` endpoint that returns text describing its current
operational state formatted in a way [Prometheus](https://prometheus.io) understands.

Prometheus is a separate open source tool that can be configured to repeatedly poll
JupyterHub's `/metrics` endpoint to parse and save its current state.

By doing so, Prometheus can describe JupyterHub's evolving state over time.
This evolving state can then be accessed through Prometheus that expose its underlying
storage to those allowed to access it, and be presented with dashboards by a
tool like [Grafana](https://grafana.com).

```{toctree}
:maxdepth: 2

/reference/metrics
```

## Customizing the metrics prefix

JupyterHub metrics all have a `jupyterhub_` prefix.
As of JupyterHub 5.0, this can be overridden with `$JUPYTERHUB_METRICS_PREFIX` environment variable
in the Hub's environment.

For example,

```bash
export JUPYTERHUB_METRICS_PREFIX=jupyterhub_prod
```

would result in the metric `jupyterhub_prod_active_users`, etc.

## Customizing spawn bucket sizes

As of JupyterHub >= 5.2.1, override `JUPYTERHUB_SERVER_SPAWN_DURATION_SECONDS_BUCKETS` env variable in Hub's environment to allow custom bucket sizes. Otherwise default to, [0.5, 1, 2.5, 5, 10, 15, 30, 60, 120, 180, 300, 600, float("inf")]

For example,

```bash
export JUPYTERHUB_SERVER_SPAWN_DURATION_SECONDS_BUCKETS="1,2,4,6,12,30,60,120"
```

## Configuring metrics

```{eval-rst}
.. currentmodule:: jupyterhub.metrics

.. autoconfigurable:: PeriodicMetricsCollector
```
