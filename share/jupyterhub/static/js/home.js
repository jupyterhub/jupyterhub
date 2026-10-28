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
  }

  function enableRow(row, running) {
    // enable buttons on a server row
    // once the server is running or not
    row.find(".btn").attr("disabled", false);
    row.find(".stop-server").click(stopServer);
    row.find(".delete-server").click(deleteServer);
    row.find(".new-server-btn").click(newServer);

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
        $("#share").hide();
        $("#start")
          .text("Start My Server")
          .attr("title", "Start your default server")
          .attr("disabled", false)
          .attr("href", base_url + "spawn/" + user)
          .off("click");
      },
    });
  });

  $("#share").click(function () {
    //TODO: add share menu and options to the modal
    var dialog = $("#share-server-dialog");
    var modal = new bootstrap.Modal(dialog[0]);
    modal.show();
    loadShareList();
    if ($("#user-list").length) {
      loadUserList();
    }
  });

  function loadUserList(offset, users) {
    offset = offset || 0;
    users = users || [];
    api.api_request("users", {
      data: "offset=" + offset,
      headers: { Accept: "application/jupyterhub-pagination+json" },
      success: function (reply) {
        users = users.concat(reply.items);
        var next = reply._pagination && reply._pagination.next;
        if (next) {
          loadUserList(next.offset, users);
          return;
        }
        var list = $("#user-list").empty();
        users.forEach(function (u) {
          if (u.name === user) return;
          list.append($("<li>").addClass("list-group-item").text(u.name));
        });
      },
    });
  }

  function loadShareList(offset, shares) {
    offset = offset || 0;
    shares = shares || [];
    api.api_request("shares/" + user + "/", {
      data: "offset=" + offset,
      success: function (reply) {
        shares = shares.concat(reply.items);
        var next = reply._pagination && reply._pagination.next;
        if (next) {
          loadShareList(next.offset, shares);
          return;
        }
        var list = $("#share-list").empty();
        shares.forEach(function (share) {
          var name = share.user ? share.user.name : share.group.name;
          var item = $("<li>").addClass("list-group-item").text(name);
          $("<button>")
            .addClass("btn btn-xs btn-danger float-end")
            .text("Revoke")
            .click(function () {
              api.api_request("shares/" + user + "/", {
                type: "PATCH",
                data: JSON.stringify(
                  share.user ? { user: name } : { group: name },
                ),
                success: function () {
                  item.remove();
                },
              });
            })
            .appendTo(item);
          list.append(item);
        });
      },
    });
  }

  $("#generate-share-link").click(function () {
    api.api_request("share-codes/" + user + "/", {
      type: "POST",
      success: function (reply) {
        var url =
          reply.full_accept_url || window.location.origin + reply.accept_url;
        $("#share-link").val(url);
        $("#share-link-group").removeClass("hidden");
      },
    });
  });

  $("#revoke-all-shares").click(function () {
    if (!confirm("Revoke access for everyone this server is shared with?")) {
      return;
    }
    api.api_request("shares/" + user + "/", {
      type: "DELETE",
      success: function () {
        $("#share-list").empty();
      },
    });
  });

  $("#copy-share-link").click(function () {
    navigator.clipboard.writeText($("#share-link").val());
  });

  $(".new-server-btn").click(newServer);
  $(".new-server-name").on("keypress", function (e) {
    if (e.which === 13) {
      newServer.call(this);
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
