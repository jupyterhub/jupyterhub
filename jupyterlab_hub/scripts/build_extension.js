var buildExtension = require('jupyterlab-extension-builder').buildExtension;

buildExtension({
        name: 'jupyterlab_hub',
        entry: './lib/plugin.js',
        outputDir: './jupyterlab_hub/static'
});
