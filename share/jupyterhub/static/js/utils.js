// Based on IPython's base.js.utils
// Original Copyright (c) IPython Development Team.
// Distributed under the terms of the Modified BSD License.

// Modifications Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

define(["jquery", "js-sha256"], function ($, sha256) {
  "use strict";

  var url_path_join = function () {
    // join a sequence of url components with '/'
    var url = "";
    for (var i = 0; i < arguments.length; i++) {
      if (arguments[i] === "") {
        continue;
      }
      if (url.length > 0 && url[url.length - 1] != "/") {
        url = url + "/" + arguments[i];
      } else {
        url = url + arguments[i];
      }
    }
    url = url.replace(/\/\/+/, "/");
    return url;
  };

  var parse_url = function (url) {
    // an `a` element with an href allows attr-access to the parsed segments of a URL
    // a = parse_url("http://localhost:8888/path/name#hash")
    // a.protocol = "http:"
    // a.host     = "localhost:8888"
    // a.hostname = "localhost"
    // a.port     = 8888
    // a.pathname = "/path/name"
    // a.hash     = "#hash"
    var a = document.createElement("a");
    a.href = url;
    return a;
  };

  var encode_uri_components = function (uri) {
    // encode just the components of a multi-segment uri,
    // leaving '/' separators
    return uri.split("/").map(encodeURIComponent).join("/");
  };

  var url_join_encode = function () {
    // join a sequence of url components with '/',
    // encoding each component with encodeURIComponent
    return encode_uri_components(url_path_join.apply(null, arguments));
  };

  var escape_html = function (text) {
    // escape text to HTML
    return $("<div/>").text(text).html();
  };

  var get_body_data = function (key) {
    // get a url-encoded item from body.data and decode it
    // we should never have any encoded URLs anywhere else in code
    // until we are building an actual request
    return decodeURIComponent($("body").data(key));
  };

  // http://stackoverflow.com/questions/2400935/browser-detection-in-javascript
  var browser = (function () {
    if (typeof navigator === "undefined") {
      // navigator undefined in node
      return "None";
    }
    var N = navigator.appName,
      ua = navigator.userAgent,
      tem;
    var M = ua.match(
      /(opera|chrome|safari|firefox|msie)\/?\s*(\.?\d+(\.\d+)*)/i,
    );
    if (M && (tem = ua.match(/version\/([\.\d]+)/i)) !== null) M[2] = tem[1];
    M = M ? [M[1], M[2]] : [N, navigator.appVersion, "-?"];
    return M;
  })();

  // http://stackoverflow.com/questions/11219582/how-to-detect-my-browser-version-and-operating-system-using-javascript
  var platform = (function () {
    if (typeof navigator === "undefined") {
      // navigator undefined in node
      return "None";
    }
    var OSName = "None";
    if (navigator.appVersion.indexOf("Win") != -1) OSName = "Windows";
    if (navigator.appVersion.indexOf("Mac") != -1) OSName = "MacOS";
    if (navigator.appVersion.indexOf("X11") != -1) OSName = "UNIX";
    if (navigator.appVersion.indexOf("Linux") != -1) OSName = "Linux";
    return OSName;
  })();

  var ajax_error_msg = function (jqXHR) {
    // Return a JSON error message if there is one,
    // otherwise the basic HTTP status text.
    if (jqXHR.responseJSON && jqXHR.responseJSON.message) {
      return jqXHR.responseJSON.message;
    } else {
      return jqXHR.statusText;
    }
  };

  var log_ajax_error = function (jqXHR, status, error) {
    // log ajax failures with informative messages
    var msg = "API request failed (" + jqXHR.status + "): ";
    console.log(jqXHR);
    msg += ajax_error_msg(jqXHR);
    console.log(msg);
    return msg;
  };

  var ajax_error_dialog = function (jqXHR, status, error) {
    console.log("ajax dialog", arguments);
    var msg = log_ajax_error(jqXHR, status, error);
    var dialog = $("#error-dialog");
    dialog.find(".ajax-error").text(msg);
    var modal = new bootstrap.Modal(dialog[0]);
    modal.show();
  };

  var safe_slug = function (name) {
    const max_length = 32;
    const _hash_length = 8;
    // Generate an always-safe, unique string for any input
    // truncates name to max_length - len(hash_suffix) to fit in max_length
    // after adding hash suffix
    const name_length = max_length - (_hash_length + 1);

    if (name_length < 1) {
      throw Error(`Cannot make safe names shorter than ${_hash_length + 2}`);
    }

    if (
      name.length < max_length &&
      /^[a-z]([a-z0-9-]*[a-z0-9])?$/.test(name) &&
      name.indexOf("-") < 0
    ) {
      return name;
    }

    // quick, short hash to avoid name collisions
    const name_hash = sha256(name).substring(0, _hash_length);

    // const safe_name = _extract_safe_name(name, name_length)
    // Generate safe substring of a name
    // Guarantees:
    // - always starts with a lowercase letter
    // - always ends with a lowercase letter or number
    // - no hyphens (so clients are free to use hyphens for other purposes)
    // - only contains lowercase letters, numbers
    // - length at least 1 ('x' if other rules strips down to empty string)
    // - max length not exceeded
    let safe_name = name
      .toLowerCase()
      .replaceAll(/[^a-z0-9]+/g, "")
      .substring(0, name_length);
    if (!safe_name) {
      safe_name = "x";
    }
    if (!/^[a-z]+/.test(safe_name)) {
      safe_name = "x" + safe_name.substring(0, name_length - 1);
    }
    // the result will always have _exactly_ one '-'
    return `${safe_name}-${name_hash}`;
  };

  var sanitise_display_name = function (name) {
    let s = name.normalize("NFC");

    // Allow letters, marks, numbers, punctuation, symbols, and spaces
    s = s.replace(/[^\p{L}\p{M}\p{N}\p{P}\p{S} ]+/gu, "");
    // Collapse multiple spaces, and leading/trailing
    s = s.replace(/ {2,}/g, " ").trim();
    return s;
  };

  var utils = {
    url_path_join: url_path_join,
    url_join_encode: url_join_encode,
    encode_uri_components: encode_uri_components,
    escape_html: escape_html,
    get_body_data: get_body_data,
    parse_url: parse_url,
    browser: browser,
    platform: platform,
    ajax_error_msg: ajax_error_msg,
    log_ajax_error: log_ajax_error,
    ajax_error_dialog: ajax_error_dialog,
    safe_slug: safe_slug,
    sanitise_display_name: sanitise_display_name,
  };

  return utils;
});
