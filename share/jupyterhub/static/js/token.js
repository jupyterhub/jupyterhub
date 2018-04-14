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
        let m = moment(new Date(el.text().trim()));
        el.text(m.isValid() ? m.fromNow() : "Never");
    });

    $("#request-token").click(function () {
        api.request_token({
            success: function (reply) {
                $("#token-result").text(reply.token);
                $("#token-area").show();
            }
        });
    });
});
