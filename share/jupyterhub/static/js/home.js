// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

require(["jquery", "moment", "jhapi"], function ($, moment, JHAPI) {
  "use strict";

  var base_url = window.jhdata.base_url;
  var user = window.jhdata.user;
  var api = new JHAPI(base_url);

  // Named servers buttons

  function getRow(element) {
    while (!element.hasClass("home-server-row")) {
      element = element.parent();
    }
    return element;
  }

  function disableRow(row) {
    row.find(".btn").attr("disabled", true).off("click");
  }

  function enableRow(row, running) {
    // enable buttons on a server row
    // once the server is running or not
    row.find(".btn").attr("disabled", false);
    row.find(".stop-server").click(stopServer);
    row.find(".delete-server").click(deleteServer);

    if (running) {
      row.find(".start-server").addClass("hidden");
      row.find(".delete-server").addClass("hidden");
      row.find(".stop-server").removeClass("hidden");
      row.find(".server-link").removeClass("hidden");
    } else {
      row.find(".start-server").removeClass("hidden");
      row.find(".delete-server").removeClass("hidden");
      row.find(".stop-server").addClass("hidden");
      row.find(".server-link").addClass("hidden");
    }
  }

  function startServer() {
    var row = getRow($(this));
    var serverName = row.find(".new-server-name").val();
    if (serverName === "") {
      // ../spawn/user/ causes a 404, ../spawn/user redirects correctly to the default server
      window.location.href = "./spawn/" + user;
    } else {
      window.location.href = "./spawn/" + user + "/" + serverName;
    }
  }

  function stopServer() {
    var row = getRow($(this));
    var serverName = row.data("server-name");

    // before request
    disableRow(row);

    // request
    api.stop_named_server(user, serverName, {
      success: function () {
        enableRow(row, false);
      },
    });
  }

  function deleteServer() {
    var row = getRow($(this));
    var serverName = row.data("server-name");

    // before request
    disableRow(row);

    // request
    api.delete_named_server(user, serverName, {
      success: function () {
        row.remove();
      },
    });
  }

  // initial state: hook up click events
  $("#stop").click(function () {
    $("#start")
      .attr("disabled", true)
      .attr("title", "Your server is stopping")
      .click(function () {
        return false;
      });
    api.stop_server(user, {
      success: function () {
        $("#stop").hide();
        $("#start")
          .text("Start My Server")
          .attr("title", "Start your default server")
          .attr("disabled", false)
          .attr("href", base_url + "spawn/" + user)
          .off("click");
      },
    });
  });

  $(".new-server-btn").click(startServer);
  $(".new-server-name").on("keypress", function (e) {
    if (e.which === 13) {
      startServer.call(this);
    }
  });

  $(".stop-server").click(stopServer);
  $(".delete-server").click(deleteServer);

  // render timestamps
  $(".time-col").map(function (i, el) {
    // convert ISO datestamps to nice momentjs ones
    el = $(el);
    var m = moment(new Date(el.text().trim()));
    el.text(m.isValid() ? m.fromNow() : "Never");
  });

  // signal that page has finished loading (mostly for tests)
  window._jupyterhub_page_loaded = true;
});
