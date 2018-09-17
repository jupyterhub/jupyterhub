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
        if ($("#start").data("named_servers") === true) {
        $("#start")
          .text("Start Default Server")
          .attr("title", "Start the default server")
          .attr("disabled", false)
          .off("click");
        } else {
        $("#start")
          .text("Start My Server")
          .attr("title", "Start your server")
          .attr("disabled", false)
          .off("click");
        $("#stop").hide();
        }
      },
    });
  });

  //// Named servers buttons

  function stop() {
    let server_name = (this.id).replace(/^(stop-)/, "");
    // before request
    $("#stop-"+server_name)
      .attr("disabled", true)
      .off("click")
      .click(function() {
        return false;});

    $("#goto-"+server_name)
      .attr("disabled", true)
      .off("click")
      .click(function() {
        return false;});

    // request
    api.stop_named_server(user, server_name, {
      success: function() {
        // after request --> establish final local state
        $("#stop-"+server_name)
          .data("state", false)
          .hide()

        $("#goto-"+server_name)
          .data("state", false)
          .hide()

        $("#start-"+server_name)
          .data("state", false)
          .show()
          .attr("disabled", false)
          .off("click")
          .click(start);
      },
    });
  };

  function goto() {
    let server_name = (this.id).replace(/^(goto-)/, "");
    // before request
    $("#stop-"+server_name)
      .attr("disabled", true)
      .off("click")
      .click(function() {
        return false;});

    $("#goto-"+server_name)
      .attr("disabled", true)
      .off("click")
      .click(function() {
        return false;});

    window.location = base_url+"/user/"+user+"/"+server_name+"/tree"; }

  function start() {
    let server_name = (this.id).replace(/^(start-)/, "");
    // before request
    $("#start-"+server_name)
      .attr("disabled", true)
      .off("click")
      .click(function() {
        return false;});

    // request
    api.start_named_server(user, server_name, {
      success: function() {
        // after request --> establish final local state
        $("#stop-"+server_name)
          .data("state", true)
          .show()
          .attr("disabled", false)
          .off("click")
          .click(stop);

        $("#goto-"+server_name)
          .data("state", true)
          .show()
          .attr("disabled", false)
          .off("click")
          .click(goto);

        $("#start-"+server_name)
          .data("state", true)
          .hide()
      }});};

  // Initial state: TRUE (server running) -- local state transitions occur by clicking stop
  // - stop visible
  // - goto visible
  // - start invisible

  $("[data-state='true'][id^='stop-']")
    .show()
    .attr("disabled", false)
    .click(stop);

  $("[data-state='true'][id^='goto-']")
    .show()
    .attr("disabled", false)
    .click(goto);

  $("[data-state='true'][id^='start-']")
    .hide()
    .attr("disabled", true)
    .off("click")
    .click(function() {
      return false;});

  // Initial state: FALSE (server not running) -- local state transitions occur by clicking start
  // - stop invisible
  // - goto invisible
  // - start visible

  $("[data-state='false'][id^='stop-']")
    .hide()
    .attr("disabled", true)
    .off("click")
    .click(function() {
      return false;});

  $("[data-state='false'][id^='goto-']")
    .hide()
    .attr("disabled", true)
    .off("click")
    .click(function() {
      return false;});

  $("[data-state='false'][id^='start-']")
    .show()
    .attr("disabled", false)
    .click(start);

});
