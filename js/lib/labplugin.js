var plugin = require('./index');
var base = require('@jupyter-widgets/base');

module.exports = {
  id: 'cad-viewer-widget:plugin',
  requires: [base.IJupyterWidgetRegistry],
  activate: function (app, widgets) {
    widgets.registerWidget({
      name: 'cad-viewer-widget',
      version: plugin.version,
      exports: plugin
    });
    console.log("JupyterLab widget 'cad-viewer-widget' is registered", plugin);
  },
  autoStart: true
};

