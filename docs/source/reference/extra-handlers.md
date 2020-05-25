# Adding extra handlers to the hub

As an alternative to [Services](./services.md), it is possible to add extra tornado handlers to the hub.

They can be used to show custom pages, expose additional API endpoints and add extra functionalities to the hub.

## Adding the handler to the JupyterHub config

Additional handlers can be created and defined in the `jupyterhub_config.py` file,
by extending [`c.JupyterHub.extra_handlers`](../api/app.html#jupyterhub.app.JupyterHub.extra_handlers).

For example:

```python
from jupyterhub.handlers.base import BaseHandler
from tornado.web import authenticated

class CustomHandler(BaseHandler):
    @authenticated
    def get(self):
        self.write(self.render_template("page.html"))

c.JupyterHub.extra_handlers.extend([
    (r"custom", CustomHandler),
])
```

Issuing a GET request to `/hub/custom` will now render the default JupyterHub page with an empty content.

## Adding a new link to the default navigation bar

The new handler can be added to the navigation bar by creating a new `page.html` file template with the following content:

```html
{% extends "templates/page.html" %}

{% block nav_bar_left_items %}
{{ super() }}
<li><a href="{{base_url}}custom">Custom Handler</a></li>
{% endblock %}
```

The `jupyterhub_config.py` file can then be updated to include the custom template:

```python
extra_template_path = "/path/to/extra/templates"
c.JupyterHub.template_paths.insert(0, extra_template_path)
```

The new handler is now visible in the naviation bar:

![extra-handlers](../images/extra-handlers.png)

See [Extending Templates](./templates.html#extending-templates) for more information on how to extend the JupyterHub UI.
