// Export widget models and views, and the npm package version number.

// eslint-disable-next-line no-undef
var widgetExports = require("./widget.js");
// eslint-disable-next-line no-undef
var sidecarExports = require("./sidecar.js");

// eslint-disable-next-line no-undef
module.exports = {...widgetExports, ...sidecarExports};

// eslint-disable-next-line no-undef
module.exports["version"] = require("../package.json").version;
