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

## Configuring metrics

```{eval-rst}
.. currentmodule:: jupyterhub.metrics

.. autoconfigurable:: PeriodicMetricsCollector
```
