#!/usr/bin/env node

var ConfigurableProxy = require('./configproxy.js').ConfigurableProxy;

var proxy = new ConfigurableProxy();
proxy.listen(8000);
