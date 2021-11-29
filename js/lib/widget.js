import "../style/index.css";

import { MainAreaWidget } from "@jupyterlab/apputils";
import { Widget } from "@lumino/widgets";
import { DOMWidgetModel, DOMWidgetView } from "@jupyter-widgets/base";
import { Viewer, Timer } from "three-cad-viewer";
import { decode } from "./serializer.js";
import { extend, isTolEqual } from "./utils.js";
import App from "./app.js";

export var CadViewerModel = DOMWidgetModel.extend({
  defaults: extend(DOMWidgetModel.prototype.defaults(), {
    _model_name: "CadViewerModel",
    _view_name: "CadViewerView",
    _model_module: "cad-viewer-widget",
    _view_module: "cad-viewer-widget",
    _model_module_version: "0.9.10",
    _view_module_version: "0.9.10",

    // Display traits

    cadWidth: null,
    height: null,
    treeWidth: null,
    theme: null,
    pinning: null,
    sidecar: null,
    anchor: null,

    // View traits

    shapes: null,
    states: null,
    tracks: null,
    timeit: null,
    tools: null,

    ortho: null,
    control: null,
    axes: null,
    axes0: null,
    grid: null,
    ticks: null,
    transparent: null,
    black_edges: null,
    normal_len: null,

    edge_color: null,
    ambient_intensity: null,
    direct_intensity: null,

    // bb_factor: null,

    // Generic UI traits

    tab: null,
    clip_intersection: null,
    clip_planes: null,
    clip_normal_0: null,
    clip_normal_1: null,
    clip_normal_2: null,
    clip_slider_0: null,
    clip_slider_1: null,
    clip_slider_2: null,

    position: null,
    quaternion: null,
    zoom: null,

    zoom_speed: null,
    pan_speed: null,
    rotate_speed: null,
    animation_speed: null,

    // Read only traitlets

    lastPick: null,
    target: null,

    initialize: null,
    image_id: null,

    result: "",
    disposed: false
  })
});

export var CadViewerView = DOMWidgetView.extend({
  render: function () {
    this.model.on("change:tracks", this.handle_change, this);
    this.model.on("change:position", this.handle_change, this);
    this.model.on("change:quaternion", this.handle_change, this);
    this.model.on("change:zoom", this.handle_change, this);
    this.model.on("change:axes", this.handle_change, this);
    this.model.on("change:grid", this.handle_change, this);
    this.model.on("change:axes0", this.handle_change, this);
    this.model.on("change:ortho", this.handle_change, this);
    this.model.on("change:transparent", this.handle_change, this);
    this.model.on("change:black_edges", this.handle_change, this);
    this.model.on("change:tools", this.handle_change, this);
    this.model.on("change:edge_color", this.handle_change, this);
    this.model.on("change:ambient_intensity", this.handle_change, this);
    this.model.on("change:direct_intensity", this.handle_change, this);
    this.model.on("change:zoom_speed", this.handle_change, this);
    this.model.on("change:pan_speed", this.handle_change, this);
    this.model.on("change:rotate_speed", this.handle_change, this);
    this.model.on("change:state_updates", this.handle_change, this);
    this.model.on("change:tab", this.handle_change, this);
    this.model.on("change:clip_intersection", this.handle_change, this);
    this.model.on("change:clip_planes", this.handle_change, this);
    this.model.on("change:clip_normal_0", this.handle_change, this);
    this.model.on("change:clip_normal_1", this.handle_change, this);
    this.model.on("change:clip_normal_2", this.handle_change, this);
    this.model.on("change:clip_slider_0", this.handle_change, this);
    this.model.on("change:clip_slider_1", this.handle_change, this);
    this.model.on("change:clip_slider_2", this.handle_change, this);
    this.model.on("change:initialize", this.initialize, this);
    this.model.on("change:js_debug", this.handle_change, this);
    this.model.on("change:disposed", this.handle_change, this);

    // this.model.on("change:bb_factor", this.handle_change, this);

    this.listenTo(this.model, "msg:custom", this.onCustomMessage.bind(this));

    this.shell = App.getShell();

    this.init = false;
    this.disposed = false;
    this.debug = this.model.get("js_debug");

    this.sidecar = this.model.get("sidecar");
    this.anchor = this.model.get("anchor");

    // old sidecar needs to be destroyed
    if (this.sidecar != null && App.getSidecarViewer(this.sidecar) != null) {
      App.getSidecarViewer(this.sidecar).widget.title.owner.dispose();
    }
    // find and remove old cell viewers, e.g. when run the same cell
    App.cleanupCellViewers();

    this.createDisplay();

    if (this.model.get("shapes") != "") {
      this.addShapes();
    }

    window.getCadViewer = App.getCadViewer;
    window.getCadViewers = App.getCadViewers;
  },

  dispose: function () {
    if (!this.disposed) {
      this.viewer.dispose();

      // first set disposed to true to avoid double dispose call
      this.disposed = true;

      if (this.sidecar != null) {
        this.widget.dispose();

        App.removeSidecarViewer(this.sidecar);

        // then set model widget, to block additional triggered dispose call
        this.widget.title.owner.disposed.disconnect(this.dispose, this);

        console.debug(
          `cad-viewer-widget: Sidecar viewer "${this.sidecar}" removed`
        );
      }

      this.model.set("disposed", true);
      this.model.save_changes();
    }
  },

  _barHandler: function (index, tab) {
    if (this.sidecar === tab.title.label) {
      this.shell._rightHandler.sideBar.tabCloseRequested.disconnect(
        this._barHandler,
        this
      );

      // this will trigger dispose()
      this.widget.title.owner.dispose();
    }
  },

  createDisplay: function () {
    const cadWidth = this.model.get("cad_width");
    const height = this.model.get("height");
    const treeWidth = this.model.get("tree_width");
    this.options = {
      cadWidth: cadWidth,
      height: height,
      treeWidth: treeWidth,
      theme: this.model.get("theme"),
      tools: this.model.get("tools"),
      pinning: this.model.get("pinning")
    };

    const container = document.createElement("div");
    container.id = `cvw_${Math.random().toString().slice(2)}`; // sufficient or uuid?

    if (this.sidecar == null) {
      App.addCellViewer(container.id, this);

      this.el.appendChild(container);
    } else {
      App.addSidecarViewer(this.sidecar, this);

      const content = new Widget();
      this.widget = new MainAreaWidget({ content });
      this.widget.addClass("cvw-sidecar");
      this.widget.id = "cad-viewer-widget";
      this.widget.title.label = this.sidecar;
      this.widget.title.closable = true;
      // this.widget.id = "cvw_" + `${Math.random()}`.slice(2);

      content.node.appendChild(container);

      if (this.anchor == "tab") {
        this.shell.add(this.widget, "main", {
          mode: "split-right"
        });
      } else {
        this.shell.add(this.widget, "right");
        this.shell._rightHandler.sideBar.tabCloseRequested.connect(
          this._barHandler,
          this
        );

        const hSplitPanel = this.shell._hsplitPanel;
        const relSizes = hSplitPanel.relativeSizes();
        const rect = hSplitPanel.node.getBoundingClientRect();
        const width = rect.width;
        const absLeft = width * relSizes[0];
        var absRight = cadWidth + treeWidth + 12;
        var absMain = width - absRight - absLeft;

        if (absMain < 0) {
          absMain = 400;
          absRight -= 400;
        }

        hSplitPanel.setRelativeSizes([
          absLeft / width,
          absMain / width,
          absRight / width
        ]);
      }
      this.widget.title.owner.disposed.connect(this.dispose, this);

      const currentWidget = this.shell.currentWidget;
      // activate sidebar
      this.shell.activateById(this.widget.id);
      // and switch back to notebook
      this.shell.activateById(currentWidget.id);
    }

    this.viewer = new Viewer(
      container,
      this.options,
      this.handleNotification.bind(this),
      this.pinAsPng.bind(this)
    );
    this.viewer.display.setAnimationControl(false);
    this.viewer.display.setTools(this.options.tools);
  },

  handleNotification: function (change) {
    var changed = false;
    Object.keys(change).forEach((key) => {
      const old_value = this.model.get(key);
      const new_value = change[key]["new"];
      if (!isTolEqual(old_value, new_value)) {
        this.model.set(key, new_value);
        changed = true;
        if (this.debug) {
          console.debug(
            `cad-viewer-widget: : Setting Python attribute ${key} to ${JSON.stringify(
              new_value,
              null,
              2
            )}`
          );
        }
      }
    });
    if (changed) {
      this.model.save_changes();
    }
  },

  clear: function () {
    this.viewer.clear();
  },

  initialize: function () {
    this.init = this.model.get("initialize");

    if (this.init) {
      this.clear();
      // this.disposeRenderers();
    } else {
      const states = this.model.get("states");
      if (Object.keys(states).length > 0) {
        this.addShapes();
      }
    }
  },

  clone_states() {
    const states = this.model.get("states");
    const states2 = {};
    for (var key in states) {
      states2[key] = states[key].slice();
    }
    return states2;
  },

  addShapes: function () {
    this.shapes = decode(this.model.get("shapes"));
    this.states = this.clone_states();
    this.options = {
      cadWidth: this.model.get("cad_width"),
      height: this.model.get("height"),
      treeWidth: this.model.get("tree_width"),
      ortho: this.model.get("ortho"),
      control: this.model.get("control"),
      axes: this.model.get("axes"),
      axes0: this.model.get("axes0"),
      grid: this.model.get("grid").slice(), // clone the array to ensure changes get detected
      ticks: this.model.get("ticks"),
      transparent: this.model.get("transparent"),
      blackEdges: this.model.get("black_edges"),
      normalLen: this.model.get("normal_len"),
      edgeColor: this.model.get("edge_color"),
      ambientIntensity: this.model.get("ambient_intensity"),
      directIntensity: this.model.get("direct_intensity"),
      timeit: this.model.get("timeit")
      // bbFactor: this.model.get("bb_factor"),
    };
    this.tracks = [];

    const timer = new Timer("addShapes", this.options.timeit);

    timer.split("viewer");

    const position = this.model.get("position");
    const quaternion = this.model.get("quaternion");
    const zoom = this.model.get("zoom");

    this.viewer.render(
      ...this.viewer.renderTessellatedShapes(this.shapes, this.states),
      this.states,
      position,
      quaternion,
      zoom
    );

    timer.split("renderer");

    this.model.set("target", this.viewer.controls.target);
    this.model.set("clip_slider_0", this.viewer.getClipSlider(0));
    this.model.set("clip_slider_1", this.viewer.getClipSlider(1));
    this.model.set("clip_slider_2", this.viewer.getClipSlider(2));
    this.model.save_changes();

    // add animation tracks if exist
    const tracks = this.model.get("tracks");
    if (tracks != "" && tracks != null) {
      this.addTracks(tracks);
      this.animate();
    }

    timer.stop();

    return true;
  },

  addTracks: function (tracks) {
    this.tracks = decode(tracks);
    if (Array.isArray(this.tracks) && this.tracks.length > 0) {
      for (var track of this.tracks) {
        this.viewer.addAnimationTrack(...track);
      }
    }
  },

  animate: function () {
    const speed = this.model.get("animation_speed");
    const duration = Math.max(
      ...this.tracks.map((track) => Math.max(...track[2]))
    );
    if (speed > 0) {
      this.viewer.initAnimation(duration, speed);
    }
  },

  clearAnimation: function () {
    // TODO: add clear to animation of three-cad-viewer
    if (this.viewer.clipAction) {
      this.viewer.controlAnimation("stop");
    }
    this.viewer.clearAnimation();
    this.tracks = [];
  },

  handle_change(change) {
    const setKey = (getter, setter, key, arg = null) => {
      const value = change.changed[key];
      const oldValue =
        arg == null ? this.viewer[getter]() : this.viewer[getter](arg);
      if (!isTolEqual(oldValue, value)) {
        if (this.debug) {
          console.debug(
            `cad-viewer-widget: Setting Javascript attribute ${key} to ${JSON.stringify(
              value,
              null,
              2
            )}`
          );
        }
        if (arg == null) {
          this.viewer[setter](value, false);
        } else {
          this.viewer[setter](arg, value, false);
        }
      }
    };

    const key = Object.keys(change.changed)[0];

    if (this.init) {
      if (this.debug) {
        console.debug("cad-viewer-widget: Ignore message");
      }
      return;
    }

    var tracks = "";
    var value = null;

    switch (key) {
      case "zoom":
        setKey("getCameraZoom", "setCameraZoom", key);
        break;
      case "position":
        setKey("getCameraPosition", "setCameraPosition", key);
        break;
      case "quaternion":
        setKey("getCameraQuaternion", "setCameraQuaternion", key);
        break;
      case "axes":
        setKey("getAxes", "setAxes", key);
        break;
      case "grid":
        setKey("getGrids", "setGrids", key);
        break;
      case "axes0":
        setKey("getAxes0", "setAxes0", key);
        break;
      case "ortho":
        setKey("getOrtho", "switchCamera", key);
        break;
      case "transparent":
        setKey("getTransparent", "setTransparent", key);
        break;
      case "black_edges":
        setKey("getBlackEdges", "setBlackEdges", key);
        break;
      case "tools":
        setKey("getTools", "setTools", key);
        break;
      case "edge_color":
        setKey("getEdgeColor", "setEdgeColor", key);
        break;
      case "ambient_intensity":
        setKey("getAmbientLight", "setAmbientLight", key);
        break;
      case "direct_intensity":
        setKey("getDirectLight", "setDirectLight", key);
        break;
      case "zoom_speed":
        setKey("getZoomSpeed", "setZoomSpeed", key);
        break;
      case "pan_speed":
        setKey("getPanSpeed", "setPanSpeed", key);
        break;
      case "rotate_speed":
        setKey("getRotateSpeed", "setRotateSpeed", key);
        break;
      case "state_updates":
        setKey("getStates", "setStates", key);
        break;
      case "tracks":
        tracks = this.model.get("tracks");
        if (tracks == "") {
          this.clearAnimation();
        } else {
          this.addTracks(tracks);
        }
        break;
      case "tab":
        value = change.changed[key];
        if (value === "tree" || value == "clip") {
          this.viewer.display.selectTabByName(value);
        } else {
          console.error(`cad-viewer-widget: unkonwn tab name ${value}`);
        }
        break;
      case "clip_intersection":
        setKey("getClipIntersection", "setClipIntersection", key);
        break;
      case "clip_planes":
        setKey("getClipPlaneHelpers", "setClipPlaneHelpers", key);
        break;
      case "clip_normal_0":
        setKey("getClipNormal", "setClipNormal", key, 0);
        break;
      case "clip_normal_1":
        setKey("getClipNormal", "setClipNormal", key, 1);
        break;
      case "clip_normal_2":
        setKey("getClipNormal", "setClipNormal", key, 2);
        break;
      case "clip_slider_0":
        setKey("getClipSlider", "setClipSlider", key, 0);
        break;
      case "clip_slider_1":
        setKey("getClipSlider", "setClipSlider", key, 1);
        break;
      case "clip_slider_2":
        setKey("getClipSlider", "setClipSlider", key, 2);
        break;
      case "js_debug":
        this.debug = change.changed[key];
        break;
      case "disposed":
        if (this.sidecar != null) {
          if (this.anchor === "right") {
            this._barHandler(0, this.widget);
          } else {
            this.widget.title.owner.dispose();
          }
        }
        break;
    }
  },

  pinAsPng: function (image) {
    this.model.set(
      "result",
      JSON.stringify({
        display_id: this.model.get("image_id"),
        src: image.src,
        width: image.width,
        height: image.height
      })
    );
    this.model.save_changes();
    // and remove itself
    this.dispose();
  },

  onCustomMessage: function (msg, buffers) {
    if (this.debug) {
      console.debug(
        "cad-viewer-widget: New message with msgType:",
        msg.type,
        "msgId:",
        msg.id,
        ", method:",
        msg.method,
        ", args:",
        msg.args,
        ", buffers:",
        buffers
      );
    }

    var object = this;
    var path = JSON.parse(msg.method);
    var method = path.pop();

    try {
      path.forEach((o) => (object = object[o]));
      if (this.debug) {
        console.debug("cad-viewer-widget: object:", object, "method:", method);
      }
    } catch (error) {
      console.error(error);
      return;
    }

    var args = null;
    try {
      args = JSON.parse(msg.args);
      if (this.debug) {
        console.debug("cad-viewer-widget: args:", args);
      }
    } catch (error) {
      console.error(error);
    }

    var result = null;
    try {
      if (args == null) {
        result = object[method]();
      } else {
        result = object[method](...args);
      }
      if (this.debug) {
        console.debug("cad-viewer-widget: method executed, result: ", result);
      }
    } catch (error) {
      console.log(error);
    }
  }
});
