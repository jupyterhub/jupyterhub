// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

require(["jquery", "jhapi", "moment"], function ($, JHAPI, moment) {
  "use strict";

  var base_url = window.jhdata.base_url;
  var user = window.jhdata.user;
  var api = new JHAPI(base_url);

  $(".time-col").map(function (i, el) {
    // convert ISO datestamps to nice momentjs ones
    el = $(el);
    var m = moment(new Date(el.text().trim()));
    el.text(m.isValid() ? m.fromNow() : el.text());
  });

  $("#request-token-form").submit(function () {
    var note = $("#token-note").val();
    if (!note.length) {
      note = "Requested via token page";
    }
    var expiration_seconds =
      parseInt($("#token-expiration-seconds").val()) || null;

    var scope_text = $("#token-scopes").val() || "";

    // split on commas and/or space
    var scope_list = scope_text.split(/[\s,]+/).filter(function (scope) {
      // filter out empty scopes
      return scope.length > 0;
    });

    var request_body = {
      note: note,
      expires_in: expiration_seconds,
    };

    if (scope_list.length > 0) {
      // add scopes to body, if defined
      request_body.scopes = scope_list;
    }

    api.request_token(user, request_body, {
      success: function (reply) {
        $("#token-result").text(reply.token);
        $("#token-area").show();
      },
    });
    return false;
  });

  function get_token_row(element) {
    while (!element.hasClass("token-row")) {
      element = element.parent();
    }
    return element;
  }

  $(".revoke-token-btn").click(function () {
    var el = $(this);
    var row = get_token_row(el);
    el.attr("disabled", true);
    api.revoke_token(user, row.data("token-id"), {
      success: function (reply) {
        row.remove();
      },
    });
  });

  // signal that page has finished loading (mostly for tests)
  window._jupyterhub_page_loaded = true;
});
