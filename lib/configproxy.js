var http = require('http'),
    httpProxy = require('http-proxy');
    // director = require('director');

var bound = function (that, method) {
    return function () {
        method.apply(that, arguments);
    };
};

var arguments_array = function (args) {
    // cast arguments object to array, because it isn't one already (?!)
    return Array.prototype.slice.call(args, 0);
};

var json_handler = function (handler) {
    // wrap json handler
    return function (req, res) {
        var args = arguments_array(arguments);
        var buf = '';
        req.on('data', function (chunk) {
            console.log('data', chunk);
            buf += chunk;
        });
        req.on('end', function () {
            console.log('buf', buf);
            try {
                data = JSON.parse(buf) || {};
            } catch (e) {
                that.fail(res, 400, "Body not valid JSON: " + e);
                return;
            }
            args.push(data);
            handler.apply(handler, args);
        });
    };
};

var ConfigurableProxy = function (options) {
    var that = this;
    this.options = options || {};
    this.upstream_port = this.options.upstream_port || 8001;
    this.default_target = 'http://localhost:' + this.upstream_port;
    this.routes = {};
    
    this.proxy = httpProxy.createProxyServer({
        ws : true
    });
    // tornado-style regex routing,
    // because cross-language cargo-culting is always a good idea
    
    this.handlers = [
        [ /^\/api\/routes$/, {
            get : bound(this, this.get_routes)
        } ],
        [ /^\/api\/routes(\/.*)$/, {
            post : json_handler(bound(this, this.post_routes)),
            'delete' : bound(this, this.delete_routes)
        } ]
    ];
    
    this.server = http.createServer(
        function (req, res) {
            try {
                return that.handle_request(req, res);
            } catch (e) {
                console.log("Error in handler for " +
                    req.method + ' ' + req.url + ': ', e
                );
            }
        }
    );
};

ConfigurableProxy.prototype.listen = function (port) {
    this.server.listen(port);
};

ConfigurableProxy.prototype.fail = function (res, code, msg) {
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
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.write(JSON.stringify(this.routes));
    res.end();
};

ConfigurableProxy.prototype.post_routes = function (req, res, path, data) {
    console.log('post', path, data);
    this.add_route(path, data);
    res.writeHead(201);
    res.end();
};

ConfigurableProxy.prototype.delete_routes = function (req, res, path) {
    console.log('delete', path);
    this.add_route(path, data);
    res.writeHead(202);
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

ConfigurableProxy.prototype.handle_request = function (req, res) {
    console.log("handle", req.method, req.url);
    for (var i = 0; i < this.handlers.length; i++) {
        var pat = this.handlers[i][0];
        var match = pat.exec(req.url);
        if (match) {
            var handlers = this.handlers[i][1];
            var handler = handlers[req.method.toLowerCase()];
            if (!handler) {
                // 405 on found resource, but not found method
                this.fail(res, 405, req.method + " " + req.url + " not supported.");
                return;
            }
            console.log("match", pat, req.url, match);
            var args = [req, res];
            match.slice(1).forEach(function (arg){ args.push(arg); });
            handler.apply(handler, args);
            return;
        }
    }
    // no local route found, time to proxy
    var target = this.target_for_url(req.url);
    console.log("proxy " + req.url + " to " + target);
    this.proxy.web(req, res, {
        target: target
    }, function (e) {
        console.log("Proxy error: ", e);
        res.writeHead(502);
        res.write("Proxy target missing");
        res.end();
    });
};

exports.ConfigurableProxy = ConfigurableProxy;