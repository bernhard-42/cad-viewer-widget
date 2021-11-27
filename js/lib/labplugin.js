// eslint-disable-next-line no-undef
var plugin = require("./index");

import { IJupyterWidgetRegistry } from "@jupyter-widgets/base";

import App from "./app.js";

const cadViewerWidget = {
  id: "cad-viewer-widget:plugin",
  requires: [IJupyterWidgetRegistry],
  activate: function (app, widgets) {
    widgets.registerWidget({
      name: "cad-viewer-widget",
      version: plugin.version,
      exports: plugin
    });
    console.log(
      `cad-viewer-widget: Widget version ${plugin.version} is registered`
    );

    App.setShell(app.shell);
  },
  autoStart: true
};

export default cadViewerWidget;
