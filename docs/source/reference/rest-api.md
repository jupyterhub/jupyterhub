<!---
This doc is part of the API references section of the References documentation.
--->

(jupyterhub-rest-API)=

# JupyterHub REST API

Below is an interactive view of JupyterHub's OpenAPI specification.

<!-- client-rendered openapi UI copied from FastAPI -->

<link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css">
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4.1/swagger-ui-bundle.js"></script>
<!-- `SwaggerUIBundle` is now available on the page -->

<!-- render the ui here -->
<div id="openapi-ui"></div>

<script>
const ui = SwaggerUIBundle({
  url: '../_static/rest-api.yml',
  dom_id: '#openapi-ui',
  presets: [
    SwaggerUIBundle.presets.apis,
    SwaggerUIBundle.SwaggerUIStandalonePreset
  ],
  layout: "BaseLayout",
  deepLinking: true,
  showExtensions: true,
  showCommonExtensions: true,
});
</script>
