// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

require(["jquery", "utils"], function ($, utils) {
  "use strict";

  var hash = utils.parse_url(window.location.href).hash;
  if (hash !== undefined && hash !== "") {
    var el = $("#start");
    var current_spawn_url = el.attr("href");
    el.attr("href", current_spawn_url + hash);
  }

  // signal that page has finished loading (mostly for tests)
  window._jupyterhub_page_loaded = true;
});
