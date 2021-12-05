import { output } from "@jupyter-widgets/jupyterlab-manager";
import App from "./app.js";
import { _module, _version } from "./version.js";

export class CadViewerSidecarModel extends output.OutputModel {
  constructor(...arg) {
    super(...arg);
    this.rendered = false;
  }

  defaults() {
    return {
      ...super.defaults(),
      _model_name: "CadViewerSidecarModel",
      _model_module: _module,
      _model_module_version: _version,
      _view_name: "CadViewerSidecarView",
      _view_module: _module,
      _view_module_version: _version,

      title: "CadViewer",
      anchor: "right",
      width: null
    };
  }

  initialize(attributes, options) {
    super.initialize(attributes, options);

    this.widget_manager.display_model(undefined, this, {});
  }
}

export class CadViewerSidecarView extends output.OutputView {
  constructor(...args) {
    super(...args);

    this.shell = App.getShell();

    this.disposed = false;
    this.widget = null;
    this.title = null;
  }

  dispose() {
    if (!this.disposed) {
      App.removeSidecar(this.title);

      // first disconnect to avoid douls dispose from child dispose
      this._outputView.title.owner.disposed.disconnect(this.dispose, this);

      if (this.child != null) {
        this.child.dispose();
      }

      console.debug(
        `cad-viewer-widget: Sidecar viewer "${this.title}" removed`
      );
    }
    this.disposed = true;
  }

  disposeSidebar(_sender, tab) {
    if (this.title === tab.title.label) {
      this.shell._rightHandler.sideBar.tabCloseRequested.disconnect(
        this.disposeSidebar,
        this
      );
      // this will trigger dispose()
      tab.title.owner.dispose();
    }
  }

  resizeSidebar() {
    const width = this.model.get("width");
    if (width != null && this.model.get("anchor") == "right") {
      const hSplitPanel = this.shell._hsplitPanel;
      const rect = hSplitPanel.node.getBoundingClientRect();
      const currentWidth = rect.width;

      const relSizes = hSplitPanel.relativeSizes();
      var absLeft = currentWidth * relSizes[0];
      // just in case
      if (isNaN(absLeft)) {
        absLeft = 0;
      }
      var absRight = width;
      var absMain = currentWidth - absRight - absLeft;

      if (absMain < 0) {
        absMain = 400;
        absRight -= 400;
      }

      hSplitPanel.setRelativeSizes([
        absLeft / currentWidth,
        absMain / currentWidth,
        absRight / currentWidth
      ]);
    }
  }

  registerChild(child) {
    this.child = child;
  }

  render() {
    this.title = this.model.get("title");

    // old sidecar needs to be destroyed
    if (this.title != null && App.getSidecar(this.title) != null) {
      App.getSidecar(this.title).widget.title.owner.dispose();
      this.model.rendered = false;
    }

    if (!this.model.rendered) {
      super.render();

      this.widget = this._outputView;

      this.widget.addClass("jupyterlab-sidecar");
      this.widget.addClass("jp-LinkedOutputView");
      this.widget.addClass("cvw-sidecar");
      this.widget.title.label = this.title;
      this.widget.title.closable = true;
      this.widget.id = `cvw_sidecar_${Math.random().toString().slice(2)}`;

      if (Object.keys(this.model.views).length > 1) {
        this.widget.node.style.display = "none";
        let key = Object.keys(this.model.views)[0];
        this.model.views[key].then((v) => {
          if (v instanceof output.OutputView) {
            v._outputView.activate();
          }
        });
      } else {
        let anchor = this.model.get("anchor") || "right";
        if (anchor === "right") {
          this.shell.add(this.widget, "right");

          this.shell._rightHandler.sideBar.tabCloseRequested.connect(
            this.disposeSidebar,
            this
          );
        } else {
          this.shell.add(this.widget, "main", { mode: anchor });

          // TODO: How to avoid overriding a protected lumino handler
          this.widget.onCloseRequest = (function (fn, scope) {
            return function (msg) {
              scope.dispose();
              fn.apply(scope.widget, msg);
            };
          })(this.widget.onCloseRequest, this);
        }

        this.widget.title.owner.disposed.connect(this.dispose, this);
        this.shell.activateById(this.widget.id);
      }

      App.addSidecar(this.title, this);
      this.model.on("change:width", this.resizeSidebar, this);

      this.model.rendered = true;

      console.debug(
        `cad-viewer-widget: Sidecar viewer "${this.title}" registered`
      );
    }

    window.currentSidecar = this;
  }
}
