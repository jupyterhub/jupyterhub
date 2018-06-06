// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

require(["jquery", "jhapi"], function($, JHAPI) {
  "use strict";

  var base_url = window.jhdata.base_url;
  var user = window.jhdata.user;
  var api = new JHAPI(base_url);

  $("#stop").click(function() {
    $("#start")
      .attr("disabled", true)
      .attr("title", "Your server is stopping")
      .click(function() {
        return false;
      });
    api.stop_server(user, {
      success: function() {
        $("#start")
          .text("Start My Server")
          .attr("title", "Start your server")
          .attr("disabled", false)
          .off("click");
        $("#stop").hide();
      }
    });
  });
});
