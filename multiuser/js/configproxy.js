// A Configurable node-http-proxy
// 
// POST, DELETE to /api/routes[:/path/to/proxy] to update the routing table
// GET /api/routes to see the current routing table
//

var http = require('http'),
    httpProxy = require('http-proxy');

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
                console.log("Error in handler for " +
                    req.method + ' ' + req.url + ': ', e
                );
            }
        };
    };
    this.api_server = http.createServer(
        log_errors(that.handle_api_request)
    );
    
    this.proxy_server = http.createServer(
        log_errors(that.handle_proxy_request)
    );
    // proxy websockets
    this.proxy_server.on('upgrade', bound(this, this.handle_ws));
};

ConfigurableProxy.prototype.fail = function (req, res, code, msg) {
    msg = msg || '';
    console.log('[' + code + '] ' + req.method + ' ' + req.url + ': ' + msg);
    res.writeHead(code);
    res.write(msg);
    res.end();
};

ConfigurableProxy.prototype.add_route = function (path, data) {
    this.routes[path] = data;
};

ConfigurableProxy.prototype.remove_route = function (path, data) {
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
    console.log('POST', path, data);
    this.add_route(path, data);
    res.writeHead(201);
    res.end();
};

ConfigurableProxy.prototype.delete_routes = function (req, res, path) {
    // DELETE removes an existing route
    console.log('DELETE', path);
    if (this.routes[path] === undefined) {
        res.writeHead(404);
    } else {
        this.remove_route(path, data);
        res.writeHead(202);
    }
    res.end();
};

ConfigurableProxy.prototype.target_for_url = function (url) {
    // return proxy target for a given url
    for (var path in this.routes) {
        if (url.indexOf(path) === 0) {
            return this.routes[path].target;
        }
    }
    // no custom target, fall back to default
    return this.default_target;
};

ConfigurableProxy.prototype.handle_ws = function (req, res, head) {
    // no local route found, time to proxy
    var target = this.target_for_url(req.url);
    console.log("PROXY WS " + req.url + " to " + target);
    this.proxy.ws(req, res, head, {
        target: target
    }, function (e) {
        console.log("Proxy error: ", e);
        res.writeHead(502);
        res.write("Proxy target missing");
        res.end();
    });
};

ConfigurableProxy.prototype.handle_proxy_request = function (req, res) {
    var target = this.target_for_url(req.url);
    console.log("PROXY " + req.method + " " + req.url + " to " + target);
    this.proxy.web(req, res, {
        target: target
    }, function (e) {
        console.log("Proxy error: ", e);
        res.writeHead(502);
        res.write("Proxy target missing");
        res.end();
    });
};

ConfigurableProxy.prototype.handle_api_request = function (req, res) {
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
            match.slice(1).forEach(function (arg){ args.push(arg); });
            handler.apply(handler, args);
            return;
        }
    }
    this.fail(req, res, 404);
};

exports.ConfigurableProxy = ConfigurableProxy;