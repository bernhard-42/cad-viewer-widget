import "../style/index.css";

import { DOMWidgetModel, DOMWidgetView } from "@jupyter-widgets/base";
import { Viewer, Display, Timer } from "three-cad-viewer";
import { decode } from "./serializer.js";
// import * as THREE from "three";

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
    _model_module_version: "0.1.0",
    _view_module_version: "0.1.0",

    // Display traits

    cadWidth: null,
    height: null,
    treeWidth: null,
    theme: null,

    // View traits

    shapes: null,
    states: null,
    tracks: null,
    needsAnimationLoop: null,
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

// function serialize(obj) {
//   try {
//     var result = JSON.stringify(obj);
//     return result;
//   } catch (error) {
//     console.error(error);
//     return "Error";
//   }
// }

// function deserialize(str) {
//   return JSON.parse(str);
// }

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

    this.model.on("change:initialize", this.initialize, this);

    // this.model.on("change:bb_factor", this.handle_change, this);

    // this.listenTo(this.model, "msg:custom", this.onCustomMessage.bind(this));

    this.init = false;
    this.is_empty = true;
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
        console.log(
          `Setting Python attribute ${key} to ${JSON.stringify(
            new_value,
            null,
            2
          )}`
        );
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
    const shapes = this.model.get("shapes");
    this.shapes = decode(shapes);
    this.states = this.model.get("states");
    this.options = {
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

    // TODO: add tracks

    this.viewer = new Viewer(
      this.display,
      this.model.get("needsAnimationLoop"),
      this.options,
      this.notificationCallback.bind(this)
    );

    const timer = new Timer("addShapes", this.options.timeit);

    timer.split("viewer");

    const position = this.model.get("position");
    const quaternion = this.model.get("quaternion");
    const zoom = this.model.get("zoom");
    console.log(position, zoom);
    this.viewer.render(this.shapes, this.states, position, quaternion, zoom);
    timer.split("renderer");

    this.is_empty = false;

    this.model.set("target", this.viewer.controls.target);
    this.model.save_changes();

    timer.stop();

    window.cadViewer = this;

    return true;
  },

  addTracks: function () {
    this.tracks = this.model.get("tracks");
    for (var track of this.tracks) {
      this.viewer.addTracks(...track);
    }
    // TODO
  },

  handle_change(change) {
    const setKey = (getter, setter, key) => {
      const value = change.changed[key];
      if (!isTolEqual(this.viewer[getter](), value)) {
        console.log(
          `Setting Javascript attribute ${key} to ${JSON.stringify(
            value,
            null,
            2
          )}`
        );
        this.viewer[setter](value, false);
      }
    };

    const key = Object.keys(change.changed)[0];
    // console.log("key", key, change.changed[key]);

    if (this.init) {
      // console.log("Ignore message");
      return;
    }

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
        setKey("getStates", "setStates", key, change.changed[key]);
        break;
    }
  }

  // onCustomMessage: function (msg, buffers) {
  //   console.log(
  //     "New message with msgType:",
  //     msg.type,
  //     "msgId:",
  //     msg.id,
  //     ", method:",
  //     msg.method,
  //     ", args:",
  //     msg.args,
  //     ", buffers:",
  //     buffers
  //   );

  //   var object = this;
  //   var path = JSON.parse(msg.method);
  //   var method = path.pop();

  //   try {
  //     path.forEach((o) => (object = object[o]));
  //   } catch (error) {
  //     console.error(error);
  //     return;
  //   }
  //   console.log("object:", object, "method:", method);

  //   var args = null;
  //   try {
  //     args = deserialize(msg.args);
  //   } catch (error) {
  //     console.error(error);
  //   }
  //   console.log("args:", args);

  //   var result = null;
  //   try {
  //     if (args == null) {
  //       result = object[method]();
  //     } else {
  //       result = object[method](...args);
  //     }
  //     console.log("method executed, result: ", result);

  //     const returnMsg = {
  //       type: "cad_viewer_method_result",
  //       id: msg.id,
  //       result: serialize(result)
  //     };
  //     console.log("sending msg with id:", msg.id, "result:", result);

  //     this.model.send(returnMsg, this.callbacks(), null);
  //   } catch (error) {
  //     console.log(error);
  //   }

  //   try {
  //     this.model.set("result", serialize({ msg_id: msg.id, result: result }));
  //     this.model.save_changes();
  //   } catch (error) {
  //     console.log(error);
  //   }
  // }
});
