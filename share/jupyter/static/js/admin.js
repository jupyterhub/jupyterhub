// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

require(["jquery", "bootstrap", "jhapi"], function ($, bs, JHAPI) {
    "use strict";
    
    var base_url = window.jhdata.base_url;
    var api = new JHAPI(base_url);
    
    var get_row = function (element) {
        while (!element.hasClass("user-row")) {
            element = element.parent();
        }
        return element;
    };
    
    $(".stop-server").click(function () {
        var el = $(this);
        var row = get_row(el);
        var user = row.data('user');
        el.text("stopping...");
        api.stop_server(user, {
            success: function () {
                window.location.reload();
            }
        });
    });

    $(".start-server").click(function () {
        var el = $(this);
        var row = get_row(el);
        var user = row.data('user');
        el.text("starting...");
        api.start_server(user, {
            success: function () {
                window.location.reload();
            }
        });
    });
    
    $(".edit-user").click(function () {
        var el = $(this);
        var row = get_row(el);
        var user = row.data('user');
        var admin = row.data('admin');
        var dialog = $("#edit-user-dialog");
        dialog.data('user', user);
        dialog.find(".username-input").val(user);
        dialog.find(".admin-checkbox").attr("checked", admin==='True');
        dialog.modal();
    });
    
    $("#edit-user-dialog").find(".save-button").click(function () {
        var dialog = $("#edit-user-dialog");
        var user = dialog.data('user');
        var name = dialog.find(".username-input").val();
        var admin = dialog.find(".admin-checkbox").prop("checked");
        api.edit_user(user, {
            admin: admin,
            name: name
        }, {
            success: function () {
                window.location.reload();
            }
        });
    });
    
    
    $(".delete-user").click(function () {
        var el = $(this);
        var row = get_row(el);
        var user = row.data('user');
        var dialog = $("#delete-user-dialog");
        dialog.find(".delete-username").text(user);
        dialog.modal();
    });

    $("#delete-user-dialog").find(".delete-button").click(function () {
        var dialog = $("#delete-user-dialog");
        var username = dialog.find(".delete-username").text();
        console.log("deleting", username);
        api.delete_user(username, {
            success: function () {
                window.location.reload();
            }
        });
    });
    
    $("#add-user").click(function () {
        var dialog = $("#add-user-dialog");
        dialog.find(".username-input").val('');
        dialog.find(".admin-checkbox").prop("checked", false);
        dialog.modal();
    });

    $("#add-user-dialog").find(".save-button").click(function () {
        var dialog = $("#add-user-dialog");
        var username = dialog.find(".username-input").val();
        var admin = dialog.find(".admin-checkbox").prop("checked");
        api.add_user(username, {admin: admin}, {
            success: function () {
                window.location.reload();
            }
        });
    });
    
});
