// A Configurable node-http-proxy
// 
// POST, DELETE to /api/routes[:/path/to/proxy] to update the routing table
// GET /api/routes to see the current routing table
//

var http = require('http'),
    httpProxy = require('http-proxy'),
    log = require('loglevel');

var bound = function (that, method) {
    // bind a method, to ensure `this=that` when it is called
    // because prototype languages are bad
    return function () {
        method.apply(that, arguments);
    };
};

var arguments_array = function (args) {
    // cast arguments object to array, because Javascript.
    return Array.prototype.slice.call(args, 0);
};

var json_handler = function (handler) {
    // wrap json handler, so the handler is called with parsed data,
    // rather than implementing streaming parsing in the handler itself
    return function (req, res) {
        var args = arguments_array(arguments);
        var buf = '';
        req.on('data', function (chunk) {
            buf += chunk;
        });
        req.on('end', function () {
            try {
                data = JSON.parse(buf) || {};
            } catch (e) {
                that.fail(req, res, 400, "Body not valid JSON: " + e);
                return;
            }
            args.push(data);
            handler.apply(handler, args);
        });
    };
};

var authorized = function (method) {
    /// decorator for token-authorized handlers
    return function (req, res) {
        if (!this.auth_token) {
            return method.apply(this, arguments);
        }
        var match = (req.headers.authorization || '').match(/token\s+(\S+)/);
        var token;
        if (match !== null) {
            token = match[1];
        }
        if (token == this.auth_token) {
            return method.apply(this, arguments);
        } else {
            res.writeHead(403);
            res.end();
        }
    };
};

var ConfigurableProxy = function (options) {
    var that = this;
    this.options = options || {};
    this.auth_token = this.options.auth_token;
    this.upstream_ip = this.options.upstream_ip || 'localhost';
    this.upstream_port = this.options.upstream_port || 8081;
    
    this.default_target = "http://" + this.upstream_ip + ":" + this.upstream_port;
    this.routes = {};
    
    var proxy = this.proxy = httpProxy.createProxyServer({
        ws : true
    });
    
    // tornado-style regex routing,
    // because cross-language cargo-culting is always a good idea
    
    this.api_handlers = [
        [ /^\/api\/routes$/, {
            get : bound(this, authorized(this.get_routes))
        } ],
        [ /^\/api\/routes(\/.*)$/, {
            post : json_handler(bound(this, authorized(this.post_routes))),
            'delete' : bound(this, authorized(this.delete_routes))
        } ]
    ];
    
    var log_errors = function(handler) {
        return function (req, res) {
            try {
                return handler.apply(that, arguments);
            } catch (e) {
                log.error("Error in handler for " +
                    req.method + ' ' + req.url + ': ', e
                );
            }
        };
    };
    
    // handle API requests
    this.api_server = http.createServer(
        log_errors(that.handle_api_request)
    );
    
    // proxy web requests separately
    this.proxy_server = http.createServer(
        log_errors(that.handle_proxy_web)
    );
    // proxy websockets
    this.proxy_server.on('upgrade', bound(this, this.handle_proxy_ws));
};

ConfigurableProxy.prototype.fail = function (req, res, code, msg) {
    // log a failure, and finish the HTTP request with an error code
    msg = msg || '';
    log.error('[' + code + ']', req.method, req.url + ':', msg);
    res.writeHead(code);
    res.write(msg);
    res.end();
};

ConfigurableProxy.prototype.add_route = function (path, data) {
    // add a route to the routing table
    this.routes[path] = data;
    this.update_last_activity(path);
};

ConfigurableProxy.prototype.remove_route = function (path) {
    // remove a route from teh routing table
    if (this.routes[path] !== undefined) {
        delete this.routes[path];
    }
};

ConfigurableProxy.prototype.get_routes = function (req, res) {
    // GET returns routing table as JSON dict
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.write(JSON.stringify(this.routes));
    res.end();
};

ConfigurableProxy.prototype.post_routes = function (req, res, path, data) {
    // POST adds a new route
    log.debug('POST', path, data);
    
    // ensure path starts with /
    if (path[0] != '/') {
        path = '/' + path;
    }
    // ensure path *doesn't* end with /
    if (path[path.length - 1] == '/') {
        path = path.substr(0, path.length - 1);
    }
    this.add_route(path, data);
    res.writeHead(201);
    res.end();
};

ConfigurableProxy.prototype.delete_routes = function (req, res, path) {
    // DELETE removes an existing route
    log.debug('DELETE', path);
    if (this.routes[path] === undefined) {
        res.writeHead(404);
    } else {
        this.remove_route(path, data);
        res.writeHead(202);
    }
    res.end();
};

var url_startswith = function (url, prefix) {
    // does the url path start with prefix?
    // use array splitting to match prefix and avoid trailing-slash and partial-word issues
    prefix_parts = prefix.split('/');
    parts = url.split('/');
    if (parts.length < prefix_parts.length) {
        return false;
    }
    for (var i = 0; i < prefix_parts.length; i++) {
         if (prefix_parts[i] != parts[i]) {
             return false;
         }
    }
    return true;
};

ConfigurableProxy.prototype.target_for_url = function (url) {
    // return proxy target for a given url path
    for (var prefix in this.routes) {
        if (url_startswith(url, prefix)) {
            return [prefix, this.routes[prefix].target];
        }
    }
    // no custom target, fall back to default
    return ['/', this.default_target];
};

ConfigurableProxy.prototype.update_last_activity = function (prefix) {
    // note last activity in routing table
    if (prefix === '/') {
        return;
    }
    this.routes[prefix].last_activity = new Date();
};

ConfigurableProxy.prototype.handle_proxy = function (kind, req, res) {
    // proxy any request
    var that = this;
    // get the proxy target
    var both = this.target_for_url(req.url);
    var prefix = both[0];
    var target = both[1];
    log.debug("PROXY", kind.toUpperCase(), req.url, "to", target);
    
    // pop method off the front
    var args = arguments_array(arguments);
    args.shift();
    
    // add config argument
    args.push({
        target: target
    });
    
    // add error handling
    args.push(function (e) {
        log.error("Proxy error: ", e);
        res.writeHead(502);
        res.write("Proxy target missing");
        res.end();
    });
    
    // update last activity timestamp in routing table
    this.update_last_activity(prefix);
    
    // update timestamp on any reply data as well (this includes websocket data)
    req.on('data', function () {
        that.update_last_activity(prefix);
    });
    res.on('data', function () {
        that.update_last_activity(prefix);
    });
    
    // dispatch the actual method
    this.proxy[kind].apply(this.proxy, args);
};

ConfigurableProxy.prototype.handle_proxy_ws = function (req, res, head) {
    // Proxy a websocket request
    return this.handle_proxy('ws', req, res, head);
};

ConfigurableProxy.prototype.handle_proxy_web = function (req, res) {
    // Proxy a web request
    return this.handle_proxy('web', req, res);
};

ConfigurableProxy.prototype.handle_api_request = function (req, res) {
    // Handle a request to the REST API
    for (var i = 0; i < this.api_handlers.length; i++) {
        var pat = this.api_handlers[i][0];
        var match = pat.exec(req.url);
        if (match) {
            var handlers = this.api_handlers[i][1];
            var handler = handlers[req.method.toLowerCase()];
            if (!handler) {
                // 405 on found resource, but not found method
                this.fail(req, res, 405, "Method not supported.");
                return;
            }
            var args = [req, res];
            match.slice(1).forEach(function (arg) { args.push(arg); });
            handler.apply(handler, args);
            return;
        }
    }
    this.fail(req, res, 404);
};

exports.ConfigurableProxy = ConfigurableProxy;