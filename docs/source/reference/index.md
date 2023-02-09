(reference-index)=

# Reference
_Reference_ documentation provide technical descriptions about JupyterHub and how it works. 
This section is divided into two broad subsections: 
1. Technical reference.
2. API reference.  
---
## Technical reference

This section covers more of the details of the JupyterHub architecture, as well as
what happens under-the-hood when you deploy and configure your JupyterHub.

### Technical overview
Provides an overview of JupyterHub's components and how they work. 

```{toctree}
:maxdepth: 1

technical-reference/technical-overview
```

### Subsystems

Find details about the different JupyterHub subsystems. 
```{toctree}
:maxdepth: 1

technical-reference/subsystems/authenticators
technical-reference/subsystems/spawners
```

### Configuration

Find useful information about configuring JupyterHub. 
```{toctree}
:maxdepth: 1

technical-reference/configuration/config-reference
technical-reference/configuration/services
technical-reference/configuration/urls
```

### Events

Find details about JupyterHub events and how to log them. 
```{toctree}
:maxdepth: 1

../events/index
```

### Monitoring

Find details about monitoring your JupyterHub deployment. 
```{toctree}
:maxdepth: 1

technical-reference/monitoring/monitoring
```

### Deployments

Find details about the institutions presently using JupyterHub. 
```{toctree}
:maxdepth: 1

technical-reference/deployments/gallery-jhub-deployments
```

### Changelog

Find details about changes to JupyterHub and its various releases.

```{toctree}
:maxdepth: 1

technical-reference/changelog/changelog
```
---
(api-index)=

## API reference

<!--
    Below is a MyST field list, using MyST substitution, as supported
    by enabling the respective MyST extensions in docs/source/conf.py.
-->

:Date: {{ date }}
:Release: {{ version }}

JupyterHub also provides a REST API for administration of the Hub and users.
The documentation on [Using JupyterHub's REST API](using-jupyterhub-rest-api) provides
information on:

- what you can do with the API
- creating an API token
- adding API tokens to the config files
- making an API request programmatically using the requests library
- learning more about JupyterHub's API

```{toctree}
:maxdepth: 1

rest-api
api-reference/app
api-reference/auth
api-reference/spawner
api-reference/proxy
api-reference/user
api-reference/service
api-reference/services.auth
```

[openapi initiative]: https://www.openapis.org/
