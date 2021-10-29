import "../style/index.css";

import { DOMWidgetModel, DOMWidgetView } from "@jupyter-widgets/base";
import { Viewer, Display, Timer } from "three-cad-viewer";
import { decode } from "./serializer.js";

// avoid loading lodash for "extend" function only
function extend(a, b) {
  Object.keys(b).forEach((key) => {
    a[key] = b[key];
  });
  return a;
}

function isThreeType(obj, type) {
  return (
    obj != null &&
    typeof obj === "object" &&
    obj.constructor != null &&
    obj.constructor.name === type
  );
}

function isTolEqual(obj1, obj2, tol = 1e-9) {
  // tolerant comparison

  // Convert three's Vector3 to arrays
  if (isThreeType(obj1, "Vector3")) {
    obj1 = obj1.toArray();
  }
  if (isThreeType(obj2, "Vector3")) {
    obj2 = obj2.toArray();
  }

  if (Array.isArray(obj1) && Array.isArray(obj2)) {
    return (
      obj1.length === obj2.length &&
      obj1.every((v, i) => isTolEqual(v, obj2[i]))
    );
  } else if (
    obj1 != null &&
    obj2 != null &&
    typeof obj1 === "object" &&
    typeof obj2 === "object"
  ) {
    var keys1 = Object.keys(obj1);
    var keys2 = Object.keys(obj2);

    if (
      keys1.length == keys2.length &&
      keys1.every((key) => Object.prototype.hasOwnProperty.call(obj2, key))
    ) {
      return keys1.every((key) => isTolEqual(obj1[key], obj2[key]));
    } else {
      return false;
    }
  } else {
    if (Number(obj1) === obj1 && Number(obj2) === obj2) {
      return Math.abs(obj1 - obj2) < tol;
    }
    return obj1 === obj2;
  }
}

export var CadViewerModel = DOMWidgetModel.extend({
  defaults: extend(DOMWidgetModel.prototype.defaults(), {
    _model_name: "CadViewerModel",
    _view_name: "CadViewerView",
    _model_module: "cad-viewer-widget",
    _view_module: "cad-viewer-widget",
    _model_module_version: "0.9.0",
    _view_module_version: "0.9.0",

    // Display traits

    cadWidth: null,
    height: null,
    treeWidth: null,
    theme: null,

    // View traits

    shapes: null,
    states: null,
    tracks: null,
    animationLoop: null,
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

    // Read only traitlets

    lastPick: null,
    target: null,

    initialize: null,
    result: ""
  })
});

export var CadViewerView = DOMWidgetView.extend({
  render: function () {
    this.createDisplay();

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

    // this.model.on("change:bb_factor", this.handle_change, this);

    this.listenTo(this.model, "msg:custom", this.onCustomMessage.bind(this));

    this.init = false;
    this.is_empty = true;
    this.debug = this.model.get("js_debug");
  },

  createDisplay: function () {
    this.options = {
      cadWidth: this.model.get("cad_width"),
      height: this.model.get("height"),
      treeWidth: this.model.get("tree_width"),
      theme: this.model.get("theme"),
      tools: this.model.get("tools")
    };
    const container = document.createElement("div");
    this.el.appendChild(container);
    this.display = new Display(container, this.options);
    this.display.setAnimationControl(false);
    this.display.setTools(this.options.tools);
  },

  notificationCallback(change) {
    var changed = false;
    Object.keys(change).forEach((key) => {
      const old_value = this.model.get(key);
      const new_value = change[key]["new"];
      if (!isTolEqual(old_value, new_value)) {
        this.model.set(key, new_value);
        changed = true;
        if (this.debug) {
          console.log(
            `Setting Python attribute ${key} to ${JSON.stringify(
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

  initialize: function () {
    this.init = this.model.get("initialize");
    if (this.init && this.viewer != null) {
      console.log("Dispose CAD object");
      this.viewer.dispose();
      this.is_empty = true;
    }

    if (!this.init && this.is_empty) {
      this.addShapes();
    }
  },

  addShapes: function () {
    this.shapes = decode(this.model.get("shapes"));

    var tracks = null;
    this.tracks = [];
    var animationLoop = this.model.get("animation_loop");
    if (this.model.get("tracks")) {
      tracks = decode(this.model.get("tracks"));
      animationLoop = true;
    }

    this.states = this.model.get("states");
    this.options = {
      cadWidth: this.model.get("cad_width"),
      height: this.model.get("height"),
      treeWidth: this.model.get("tree_width"),
      ortho: this.model.get("ortho"),
      control: this.model.get("control"),
      axes: this.model.get("axes"),
      axes0: this.model.get("axes0"),
      grid: this.model.get("grid"),
      ticks: this.model.get("ticks"),
      transparent: this.model.get("transparent"),
      blackEdges: this.model.get("black_edges"),
      edgeColor: this.model.get("edge_color"),
      ambientIntensity: this.model.get("ambient_intensity"),
      directIntensity: this.model.get("direct_intensity"),
      timeit: this.model.get("timeit")
      // bbFactor: this.model.get("bb_factor"),
    };

    this.viewer = new Viewer(
      this.display,
      animationLoop,
      this.options,
      this.notificationCallback.bind(this)
    );

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

    this.is_empty = false;

    this.model.set("target", this.viewer.controls.target);
    this.model.set("clip_slider_0", this.viewer.getClipSlider(0));
    this.model.set("clip_slider_1", this.viewer.getClipSlider(1));
    this.model.set("clip_slider_2", this.viewer.getClipSlider(2));
    this.model.save_changes();

    // add animation tracks if exists
    this.addTracks(tracks);

    timer.stop();

    window.cadViewer = this;

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

  animate: function (speed) {
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
          console.log(
            `Setting Javascript attribute ${key} to ${JSON.stringify(
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
        console.log("Ignore message");
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
          console.error(`unkonwn tab name ${value}`);
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
    }
  },

  onCustomMessage: function (msg, buffers) {
    if (this.debug) {
      console.log(
        "New message with msgType:",
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
        console.log("object:", object, "method:", method);
      }
    } catch (error) {
      console.error(error);
      return;
    }

    var args = null;
    try {
      args = JSON.parse(msg.args);
      if (this.debug) {
        console.log("args:", args);
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
        console.log("method executed, result: ", result);
      }
    } catch (error) {
      console.log(error);
    }
  }
});
