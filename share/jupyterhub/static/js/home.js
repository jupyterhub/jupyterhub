// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

require(["jquery", "moment", "jhapi", "utils"], function (
  $,
  moment,
  JHAPI,
  utils,
) {
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
    row.find(".start-server").prop("disabled", true).addClass("disabled");
    row.find(".start-server").text("pend");
  }

  function enableRow(row, running) {
    // enable buttons on a server row
    // once the server is running or not
    row.find(".btn").attr("disabled", false);
    row.find(".start-server").click(startServer);
    row.find(".stop-server").click(stopServer);
    row.find(".delete-server").click(deleteServer);
    row.find(".new-server-btn").click(newServer);

    if (running) {
      row.find(".start-server").addClass("hidden");
      row.find(".spawn-server").addClass("hidden");
      row.find(".delete-server").addClass("hidden");
      row.find(".stop-server").removeClass("hidden");
      row.find(".access-server").removeClass("hidden");
      row.find(".server-link").removeClass("hidden");
    } else {
      row.find(".start-server").prop("disabled", false).removeClass("disabled");
      row.find(".start-server").text("start");
      row.find(".start-server").removeClass("hidden");
      row.find(".spawn-server").removeClass("hidden");
      row.find(".delete-server").removeClass("hidden");
      row.find(".stop-server").addClass("hidden");
      row.find(".access-server").addClass("hidden");
      row.find(".server-link").addClass("hidden");
    }
  }

  function startDefault() {
    // before request
    $("#start-default").prop("disabled", true).addClass("disabled");
    $("#start-default").text("Server is pending");

    // request
    api.start_server(user, {
      success: function () {
        $("#start-default").addClass("hidden");
        $("#spawn-default").addClass("hidden");
        $("#stop-default").removeClass("hidden");
        $("#access-default").removeClass("hidden");
      },
    });
  }

  function stopDefault() {
    // before request
    $("#start-default").prop("disabled", false).removeClass("disabled");
    $("#start-default").text("Start My Server");

    // request
    api.stop_server(user, {
      success: function () {
        $("#start-default").removeClass("hidden");
        $("#spawn-default").removeClass("hidden");
        $("#stop-default").addClass("hidden");
        $("#access-default").addClass("hidden");
      },
    });
  }

  function newServer() {
    var row = getRow($(this));
    var displayName = row.find(".new-server-name").val();
    displayName = utils.sanitise_display_name(displayName);
    var serverName = utils.safe_slug(displayName);
    disableRow(row);
    api.create_named_server(user, serverName, {
      success: function () {
        window.location.reload();
      },
      error: function () {
        enableRow(row, false);
        return utils.ajax_error_dialog.apply(this, arguments);
      },
      data: JSON.stringify({ display_name: displayName }),
    });
  }

  function startServer() {
    var row = getRow($(this));
    var serverName = row.data("server-name");

    // before request
    disableRow(row);

    // request
    api.start_named_server(user, serverName, {
      success: function () {
        enableRow(row, true);
      },
    });
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

    if (
      window.confirm(
        `Are you sure you want to delete your server "${serverName}"?`,
      )
    ) {
      // before request
      disableRow(row);

      // request
      api.delete_named_server(user, serverName, {
        success: function () {
          row.remove();
        },
      });
    }
  }

  // initial state: hook up click events
  $(".start-default").click(startDefault);
  $(".stop-default").click(stopDefault);

  $(".new-server-btn").click(newServer);
  $(".new-server-name").on("keypress", function (e) {
    if (e.which === 13) {
      newServer.call(this);
    }
  });

  $(".start-server").click(startServer);
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
