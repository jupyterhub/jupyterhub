Monitoring
==========

This section covers details on monitoring the state of your JupyterHub installation.

JupyterHub expose the ``/metrics`` endpoint that returns text describing its current
operational state formatted in a way `Prometheus <https://prometheus.io/docs/introduction/overview/>`_ understands.

Prometheus is a separate open source tool that can be configured to repeatedly poll
JupyterHub's ``/metrics`` endpoint to parse and save its current state.

By doing so, Prometheus can describe JupyterHub's evolving state over time.
This evolving state can then be accessed through Prometheus that expose its underlying
storage to those allowed to access it, and be presented with dashboards by a
tool like `Grafana <https://grafana.com/docs/grafana/latest/getting-started/what-is-grafana/>`_.

.. toctree::
   :maxdepth: 2

   metrics
