#!/usr/bin/env node
/*
cli entrypoint for starting a Configurable Proxy

*/
var fs = require('fs');
var args = require('commander');

args
    .version('0.0.0')
    // .option('-h', '--help', 'show help')
    .option('--key <keyfile>', 'SSL key to use, if any')
    .option('--cert <certfile>', 'SSL certificate to use, if any')
    .option('--ip <n>', 'Public-facing IP of the proxy', parseInt)
    .option('--port <n>', 'Public-facing port of the proxy', parseInt)
    .option('--upstream-ip <ip>', 'IP address of the default proxy target', 'localhost')
    .option('--upstream-port <n>', 'Port of the default proxy target', parseInt)
    .option('--api-ip <ip>', 'Inward-facing IP for API request', 'localhost')
    .option('--api-port <n>', 'Inward-facing port for API request', parseInt)

args.parse(process.argv);

var ConfigurableProxy = require('./configproxy.js').ConfigurableProxy;

var options = {};
if (args.key) {
    options.key = fs.readFileSync(args.key);
}

if (args.cert) {
    options.cert = fs.readFileSync(args.cert);
}

// because camelCase is the js way!
options.upstream_ip = args.upstreamIp;
options.upstream_port = args.upstreamPort;
options.auth_token = process.env.CONFIGPROXY_AUTH_TOKEN;

var proxy = new ConfigurableProxy(options);

var listen = {};
listen.port = args.port || 8000;
listen.ip = args.ip;
listen.api_ip = args.apiIp || 'localhost';
listen.api_port = args.apiPort || listen.port + 1;

proxy.proxy_server.listen(listen.port, listen.ip);
proxy.api_server.listen(listen.api_port, listen.api_ip);

console.log("Proxying %s:%s to %s:%s", (listen.ip || '*'), listen.port,
    proxy.upstream_ip, proxy.upstream_port
);
console.log("Proxy API at %s:%s/api/routes", (listen.api_ip || '*'), listen.api_port);

