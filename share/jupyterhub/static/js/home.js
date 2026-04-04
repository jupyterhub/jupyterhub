// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

require(["jquery", "moment", "jhapi"], function ($, moment, JHAPI) {
  "use strict";

  var base_url = window.jhdata.base_url;
  var user = window.jhdata.user;
  var api = new JHAPI(base_url);

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
    row.find(".btn").attr("disabled", false);
    row.find(".stop-server").click(stopServer);

    //  attach new handler instead of old deleteServer
    attachCloneUndoHandler();

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
      window.location.href = "./spawn/" + user;
    } else {
      window.location.href = "./spawn/" + user + "/" + serverName;
    }
  }

  function stopServer() {
    var row = getRow($(this));
    var serverName = row.data("server-name");

    disableRow(row);

    api.stop_named_server(user, serverName, {
      success: function () {
        enableRow(row, false);
      },
    });
  }

  // -----------------------------
  // NEW: Clone + Undo Delete Handler
  // -----------------------------
  function attachCloneUndoHandler() {
    $(document)
      .off("click", ".delete-server")
      .on("click", ".delete-server", function (e) {
        e.preventDefault();
        e.stopImmediatePropagation();

        var row = $(this).closest(".home-server-row");
        var serverName = row.data("server-name");
        var btn = $(this);

        // Prevent re-entry
        if (btn.data("processing")) return;

        // If already in undo mode → ignore main handler
        if (btn.data("undoMode")) return;

        if (!confirm(`⚠️Delete server "${serverName}"?`)) return;

        function startCountdown() {
          let countdown = 10;
          let cancelled = false;

          btn.data("processing", true);
          btn.data("undoMode", true);
          btn.text(`Undo delete (${countdown}s)`);

          const interval = setInterval(() => {
            countdown--;
            btn.text(`Undo delete (${countdown}s)`);

            if (countdown <= 0) {
              clearInterval(interval);

              if (!cancelled) {
                btn.text("Deleting...");

                //  use JupyterHub API (fix)
                api.delete_named_server(user, serverName, {
                  success: function () {
                    setTimeout(() => location.reload(), 2000);
                  },
                });
              }
            }
          }, 1000);

          //  Proper undo handler
          btn.off("click.undo").on("click.undo", function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();

            cancelled = true;
            clearInterval(interval);

            btn.text("Delete");
            btn.data("processing", false);
            btn.data("undoMode", false);

            // Remove undo handler only
            btn.off("click.undo");
          });
        }

        // Clone step
        if (confirm(`Do you want to clone "${serverName}" before deleting?`)) {
          let cloneName = prompt("Enter new server name:");

          if (cloneName) {
            btn.text("Cloning...");
            btn.prop("disabled", true);

            api.start_named_server(user, cloneName, {
              success: function () {
                alert(
                  ` Clone "${cloneName}" created successfully.\n\nYou can now delete the old server "${serverName}".`,
                );

                btn.text("Delete");
                btn.prop("disabled", false);
                btn.data("processing", false);

                setTimeout(() => location.reload(), 2000);
              },
              error: function () {
                alert(" Clone failed. Deletion cancelled.");
                btn.text("Delete");
                btn.prop("disabled", false);
                btn.data("processing", false);
              },
            });
          } else {
            startCountdown();
          }
        } else {
          startCountdown();
        }
      });
  }

  // initial state
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

  // attach new delete logic
  attachCloneUndoHandler();

  $(".time-col").map(function (i, el) {
    el = $(el);
    var m = moment(new Date(el.text().trim()));
    el.text(m.isValid() ? m.fromNow() : "Never");
  });

  window._jupyterhub_page_loaded = true;
});
