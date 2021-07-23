// eslint-disable-next-line no-undef
var plugin = require("./index");
// eslint-disable-next-line no-undef
var base = require("@jupyter-widgets/base");

// eslint-disable-next-line no-undef
module.exports = {
  id: "cad-viewer-widget:plugin",
  requires: [base.IJupyterWidgetRegistry],
  activate: function (app, widgets) {
    widgets.registerWidget({
      name: "cad-viewer-widget",
      version: plugin.version,
      exports: plugin
    });
    console.log("Widget 'cad-viewer-widget' is registered");
  },
  autoStart: true
};
