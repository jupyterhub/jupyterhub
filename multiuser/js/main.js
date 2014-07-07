#!/usr/bin/env node
/*
cli entrypoint for starting a Configurable Proxy

*/
var fs = require('fs');
var minimist = require('minimist');
var ConfigurableProxy = require('./configproxy.js').ConfigurableProxy;

var argv = minimist(process.argv.slice(2), {boolean: ['h', 'help']});

if (argv.h || argv.help) {
    console.log("help!");
    process.exit();
}

var options = {};
if (argv.ssl_key) {
    options.key = fs.readFileSync(argv.ssl_key);
}

if (argv.ssl_cert) {
    options.cert = fs.readFileSync(argv.ssl_cert);
}

options.upstream_ip = argv.upstream_ip;
options.upstream_port = argv.upstream_port;
options.api_token = process.env.CONFIGPROXY_AUTH_TOKEN;

var proxy = new ConfigurableProxy(options);

var listen = {};
listen.port = argv.port || 8000;
listen.ip = argv.ip;
listen.api_ip = argv.api_ip || 'localhost';
listen.api_port = argv.api_port || listen.port + 1;


proxy.proxy_server.listen(listen.port, listen.ip);
// proxy.api_server(listen.api_port, listen.api_ip);

console.log(
    "Proxying " + (listen.ip || '*') + ":" + listen.port +
    " to " + proxy.upstream_ip + ":" + proxy.upstream_port
);

if (options.api_ip || options.api_port) {
    console.log("API entry points on " + (listen.api_ip || '*') + ":" + listen.api_port);
}

