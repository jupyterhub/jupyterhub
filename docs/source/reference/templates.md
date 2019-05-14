# Working with templates and UI

The pages of the JupyterHub application are generated from
[Jinja](http://jinja.pocoo.org/) templates.  These allow the header, for
example, to be defined once and incorporated into all pages.  By providing
your own templates, you can have complete control over JupyterHub's
appearance.

## Custom Templates

JupyterHub will look for custom templates in all of the paths in the
`JupyterHub.template_paths` configuration option, falling back on the
[default templates](https://github.com/jupyterhub/jupyterhub/tree/master/share/jupyterhub/templates)
if no custom template with that name is found. This fallback
behavior is new in version 0.9; previous versions searched only those paths
explicitly included in `template_paths`. You may override as many
or as few templates as you desire.

## Extending Templates

Jinja provides a mechanism to [extend templates](http://jinja.pocoo.org/docs/2.10/templates/#template-inheritance).
A base template can define a `block`, and child templates can replace or
supplement the material in the block.  The 
[JupyterHub templates](https://github.com/jupyterhub/jupyterhub/tree/master/share/jupyterhub/templates)
make extensive use of blocks, which allows you to customize parts of the
interface easily.

In general, a child template can extend a base template, `page.html`, by beginning with:

```html
{% extends "page.html" %}
```

This works, unless you are trying to extend the default template for the same
file name.  Starting in version 0.9, you may refer to the base file with a
`templates/` prefix.  Thus, if you are writing a custom `page.html`, start the
file with this block:

```html
{% extends "templates/page.html" %}
```

By defining `block`s with same name as in the base template, child templates
can replace those sections with custom content.  The content from the base
template can be included with the `{{ super() }}` directive.

### Example

To add an additional message to the spawn-pending page, below the existing
text about the server starting up, place this content in a file named
`spawn_pending.html` in a directory included in the
`JupyterHub.template_paths` configuration option.

```html
{% extends "templates/spawn_pending.html" %}

{% block message %}
{{ super() }}
<p>Patience is a virtue.</p>
{% endblock %}
```

## Page Announcements

To add announcements to be displayed on a page, you have two options:

- Extend the page templates as described above
- Use configuration variables

### Announcement Configuration Variables

If you set the configuration variable `JupyterHub.template_vars =
{'announcement': 'some_text'}`, the given `some_text` will be placed on
the top of all pages.  The more specific variables
`announcement_login`, `announcement_spawn`, `announcement_home`, and
`announcement_logout` are more specific and only show on their
respective pages (overriding the global `announcement` variable).
Note that changing these variables require a restart, unlike direct
template extension.

You can get the same effect by extending templates, which allows you
to update the messages without restarting.  Set
`c.JupyterHub.template_paths` as mentioned above, and then create a
template (for example, `login.html`) with:

```html
{% extends "templates/login.html" %}
{% set announcement = 'some message' %}
```

Extending `page.html` puts the message on all pages, but note that
extending `page.html` take precedence over an extension of a specific
page (unlike the variable-based approach above).
