
# Simple Announcement Service Example

This is a simple service that allows administrators to manage announcements
that appear when JupyterHub renders pages.

To run the service as a hub-managed service simply include in your JupyterHub
configuration file something like:

    c.JupyterHub.services = [
            {
                'name': 'announcement',
                'url': 'http://127.0.0.1:8888',
                'command': [sys.executable, "-m", "announcement"],
            }
    ]

This starts the announcements service up at `/services/announcement` when
JupyterHub launches.  By default the announcement text is empty.

The `announcement` module has a configurable port (default 8888) and an API
prefix setting.  By default the API prefix is `JUPYTERHUB_SERVICE_PREFIX` if
that environment variable is set or `/` if it is not.

## Managing the Announcement

Admin users can set the announcement text with an API token:

    $ curl -X POST -H "Authorization: token <token>"                        \
        -d "{'announcement':'JupyterHub will be upgraded on August 14!'}"   \
        https://.../services/announcement

Anyone can read the announcement:

    $ curl https://.../services/announcement | python -m json.tool
    {
        announcement: "JupyterHub will be upgraded on August 14!",
        timestamp: "...",
        user: "..."
    }

The time the announcement was posted is recorded in the `timestamp` field and
the user who posted the announcement is recorded in the `user` field.

To clear the announcement text, just DELETE.  Only admin users can do this.

    $ curl -X POST -H "Authorization: token <token>"                        \
        https://.../services/announcement

## Seeing the Announcement in JupyterHub

To be able to render the announcement, include the provide `page.html` template
that extends the base `page.html` template.  Set `c.JupyterHub.template_paths`
in JupyterHub's configuration to include the path to the extending template.
The template changes the `announcement` element and does a JQuery `$.get()` call
to retrieve the announcement text.

JupyterHub's configurable announcement template variables can be set for various
pages like login, logout, spawn, and home.  Including the template provided in
this example overrides all of those.
