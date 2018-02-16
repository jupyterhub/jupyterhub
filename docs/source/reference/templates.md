# Templates

The pages of the JupyterHub application are generated from [Jinja](http://jinja.pocoo.org/) templates.  These allow the header, for example, to be defined once and incorporated into all pages.  By providing your own templates, you can have complete control over JupyterHub's appearance.

## Custom Templates

JupyterHub will look for custom templates in all of the paths in the `JupyterHub.template_paths` configuration option, falling back on the [default templates](https://github.com/jupyterhub/jupyterhub/tree/master/share/jupyter/hub/templates) if no custom template with that name is found.  This means you can override as many or as few templates as you desire.

## Extending Templates

Jinja provides a mechanism to [extend templates](http://jinja.pocoo.org/docs/2.10/templates/#template-inheritance).  A base template can define a `block`, and child templates can replace or supplement the material in the block.  The [JupyterHub templates](https://github.com/jupyterhub/jupyterhub/tree/master/share/jupyter/hub/templates) make extensive use of this feature, which allows you to customize parts of the interface easily.

In general, a child template can extend a base template, `base.html`, by beginning with
```
{% extends "base.html" %}
```
This works, unless you are trying to extend the default template for the same file name.  In this case, refer to the base file with a `templates/` prefix.  Thus, if you are writing a custom `base.html`, start it with
```
{% extends "templates/base.html" %}
```
By defining `block`s with same name as in the base template, child templates can replace those sections with custom content.  The content from the base template can be included with the `{{ super() }}` directive.

### Example

To add an additional message to the spawn-pending page, below the existing text about the server starting up, place this content in a file named `spawn_pending.html` in a directory included in the `JupyterHub.template_paths` configuration option.

```html
{% extends "templates/spawn_pending.html" %}

{% block message %}
{{ super() }}
<p>Patience is a virtue.</p>
{% endblock %}
```
