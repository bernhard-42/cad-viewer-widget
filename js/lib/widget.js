import "../style/index.css";

import { DOMWidgetModel, DOMWidgetView } from "@jupyter-widgets/base";
import { Viewer, Display, Timer } from "three-cad-viewer";
import { decode } from "./serializer.js";
import * as THREE from "three";

// avoid loading lodash for "extend" function only
function extend(a, b) {
  Object.keys(b).forEach((key) => {
    a[key] = b[key];
  });
  return a;
}

function isTolEqual(obj1, obj2, tol = 1e-9) {
  if (Array.isArray(obj1) && Array.isArray(obj2)) {
    return (
      obj1.length === obj2.length &&
      obj1.every((v, i) => isTolEqual(v, obj2[i]))
    );
  } else if (typeof obj1 === "object" && typeof obj2 === "object") {
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

    // Display parameters
    cadWidth: null,
    height: null,
    treeWidth: null,
    theme: null,

    // View parameters
    shapes: null,
    states: null,

    timeit: null,
    needsAnimationLoop: null,

    tab: null,
    ortho: null,
    control: null,
    axes: null,
    grid: null,
    axes0: null,
    transparent: null,
    black_edges: null,

    zoom_speed: null,
    pan_speed: null,
    rotate_speed: null,

    clip_intersection: null,
    clip_planes: null,
    clip_normal_0: null,
    clip_normal_1: null,
    clip_normal_2: null,
    clip_slider_0: null,
    clip_slider_1: null,
    clip_slider_2: null,

    tracks: null,

    position: null,
    zoom: null,

    bb_factor: null,
    tools: null,
    edge_color: null,
    ambient_intensity: null,
    direct_intensity: null,

    lastPick: null,
    target: null,

    result: ""
  })
});

function serialize(obj) {
  try {
    var result = JSON.stringify(obj);
    return result;
  } catch (error) {
    console.error(error);
    return "Error";
  }
}

function deserialize(str) {
  return JSON.parse(str);
}

export var CadViewerView = DOMWidgetView.extend({
  render: function () {
    this.createDisplay();
    this.model.on("change:shapes", this.addShapes, this);
    this.model.on("change:tracks", this.addTracks, this);
    this.model.on("change:states", this.handle_change, this);
    this.model.on("change:position", this.handle_change, this);
    this.model.on("change:zoom", this.handle_change, this);
    this.model.on("change:axes", this.handle_change, this);
    this.model.on("change:grid", this.handle_change, this);
    this.model.on("change:axes0", this.handle_change, this);
    this.model.on("change:ortho", this.handle_change, this);
    this.model.on("change:transparent", this.handle_change, this);
    this.model.on("change:black_edges", this.handle_change, this);
    this.model.on("change:bb_factor", this.handle_change, this);
    this.model.on("change:tools", this.handle_change, this);
    this.model.on("change:edge_color", this.handle_change, this);
    this.model.on("change:ambient_intensity", this.handle_change, this);
    this.model.on("change:direct_intensity", this.handle_change, this);
    this.model.on("change:zoom_speed", this.handle_change, this);
    this.model.on("change:pan_speed", this.handle_change, this);
    this.model.on("change:rotate_speed", this.handle_change, this);

    this.listenTo(this.model, "msg:custom", this.onCustomMessage.bind(this));
  },

  createDisplay: function () {
    this.options = {
      cadWidth: this.model.get("cadWidth"),
      height: this.model.get("height"),
      treeWidth: this.model.get("treeWidth"),
      theme: this.model.get("theme"),
      timeit: this.model.get("timeit"),
      needsAnimationLoop: this.model.get("needsAnimationLoop"),
      tools: this.model.get("tools")
    };
    const container = document.createElement("div");
    this.el.appendChild(container);
    this.display = new Display(container, this.options);
    this.display.setAnimationControl(false);
    this.display.setTools(this.options.tools);
    this.hasShapes = false;
  },

  notificationCallback(change) {
    Object.keys(change).forEach((key) => {
      if (key === "camera_position" || key == "camera_zoom") {
        // remove the prefix to be compliant with traitlets
        this.model.set(key.slice(7), change[key]["new"]);
      } else {
        this.model.set(key, change[key]["new"]);
      }
      console.log("==> Python: setting", key, "to", change[key]["new"]);
    });
    this.model.save_changes();
  },

  addShapes: function () {
    const shapes = this.model.get("shapes");
    this.shapes = decode(shapes);
    this.states = this.model.get("states");
    this.options = {
      axes: this.model.get("axes"),
      grid: this.model.get("grid"),
      axes0: this.model.get("axes0"),
      ortho: this.model.get("ortho"),
      control: this.model.get("control"),
      ticks: this.model.get("ticks"),
      transparent: this.model.get("transparent"),
      blackEdges: this.model.get("black_edges"),
      bbFactor: this.model.get("bb_factor"),
      edgeColor: this.model.get("edge_color"),
      ambientIntensity: this.model.get("ambient_intensity"),
      directIntensity: this.model.get("direct_intensity")
    };

    const timeit = this.model.get("timeit");

    const timer = new Timer("addShapes", timeit);
    this.viewer = new Viewer(
      this.display,
      this.model.get("needsAnimationLoop"),
      this.options,
      this.notificationCallback.bind(this)
    );

    this.viewer._timeit = timeit;

    timer.split("viewer");

    this.viewer.render(this.shapes, this.states);
    timer.split("renderer");

    this.hasShapes = true;

    // console.log("target", this.viewer.controls.target.toArray());
    this.model.set("target", this.viewer.controls.target);
    this.model.save_changes();

    timer.stop();

    window.cadViewer = this;
  },

  addTracks: function () {
    this.tracks = this.model.get("tracks");
    for (var track of this.tracks) {
      this.viewer.addTracks(...track);
    }
    // TODO
  },

  handle_change(change) {
    if (!this.hasShapes) {
      return;
    }

    const key = Object.keys(change.changed)[0];

    switch (key) {
      case "zoom":
        if (!isTolEqual(this.viewer.getCameraZoom(), change.changed[key])) {
          console.log(
            "==> Javascript: setting camera_zoom to ",
            change.changed[key]
          );
          this.viewer.setCameraZoom(change.changed[key], false);
        }
        break;
      case "position":
        if (
          !isTolEqual(
            this.viewer.getCameraPosition().toArray(),
            change.changed[key]
          )
        ) {
          console.log(
            "==> Javascript: setting camera_position to ",
            change.changed[key]
          );
          this.viewer.setCameraPosition(change.changed[key], false, false);
        }
        break;
      case "axes":
        if (!isTolEqual(this.viewer.getAxes(), change.changed[key])) {
          console.log("==> Javascript: setting axes to ", change.changed[key]);
          this.viewer.setAxes(change.changed[key], false);
        }
        break;
      case "grid":
        if (!isTolEqual(this.viewer.getGrids(), change.changed[key])) {
          console.log("==> Javascript: setting grid to ", change.changed[key]);
          this.viewer.setGrids(...change.changed[key], false);
        }
        break;
      case "axes0":
        if (!isTolEqual(this.viewer.getAxes0(), change.changed[key])) {
          console.log("==> Javascript: setting axes0 to ", change.changed[key]);
          this.viewer.setAxes0(change.changed[key], false);
        }
        break;
      case "ortho":
        if (!isTolEqual(this.viewer.getOrtho(), change.changed[key])) {
          console.log("==> Javascript: setting ortho to ", change.changed[key]);
          this.viewer.switchCamera(change.changed[key], false, false);
        }
        break;
      case "transparent":
        if (!isTolEqual(this.viewer.getTransparent(), change.changed[key])) {
          console.log(
            "==> Javascript: setting transparent to ",
            change.changed[key]
          );
          this.viewer.setTransparent(change.changed[key], false);
        }
        break;
      case "black_edges":
        if (!isTolEqual(this.viewer.getBlackEdges(), change.changed[key])) {
          console.log(
            "==> Javascript: setting black_edges to ",
            change.changed[key]
          );
          this.viewer.setBlackEdges(change.changed[key], false);
        }
        break;
      // case "bb_factor":
      //   if (!isEqual(this.viewer.getBb_factor(), change.changed[key])) {
      //     console.log("==> Javascript: setting bb_factor to ", change.changed[key]);
      //     this.viewer.bb_factor = change.changed[key];
      //   }
      //   break;
      case "tools":
        console.log(this.viewer.getTools(), change.changed[key]);
        if (!isTolEqual(this.viewer.getTools(), change.changed[key])) {
          console.log("==> Javascript: setting tools to ", change.changed[key]);
          this.viewer.setTools(change.changed[key], false);
        }
        break;
      case "edge_color":
        if (!isTolEqual(this.viewer.getEdgeColor(), change.changed[key])) {
          console.log(
            "==> Javascript: setting edge_color to ",
            change.changed[key]
          );
          this.viewer.setEdgeColor(change.changed[key], false);
        }
        break;
      case "ambient_intensity":
        if (!isTolEqual(this.viewer.getAmbientLight(), change.changed[key])) {
          console.log(
            "==> Javascript: setting ambient_intensity to ",
            change.changed[key]
          );
          this.viewer.setAmbientLight(change.changed[key], false);
        }
        break;
      case "direct_intensity":
        if (!isTolEqual(this.viewer.getDirectLight(), change.changed[key])) {
          console.log(
            "==> Javascript: setting direct_intensity to ",
            change.changed[key]
          );
          this.viewer.setDirectLight(change.changed[key], false);
        }
        break;
      case "zoom_speed":
        if (!isTolEqual(this.viewer.getZoomSpeed(), change.changed[key])) {
          console.log(
            "==> Javascript: setting zoom_speed to ",
            change.changed[key]
          );
          this.viewer.setZoomSpeed(change.changed[key], false);
        }
        break;
      case "pan_speed":
        if (!isTolEqual(this.viewer.getPanSpeed(), change.changed[key])) {
          console.log(
            "==> Javascript: setting pan_speed to ",
            change.changed[key]
          );
          this.viewer.setPanSpeed(change.changed[key], false);
        }
        break;
      case "rotate_speed":
        if (!isTolEqual(this.viewer.getRotateSpeed(), change.changed[key])) {
          console.log(
            "==> Javascript: setting rotate_speed to ",
            change.changed[key]
          );
          this.viewer.setRotateSpeed(change.changed[key], false);
        }
        break;
      case "states":
        if (!isTolEqual(this.viewer.getStates(), change.changed[key])) {
          console.log(
            "==> Javascript: setting states to ",
            change.changed[key]
          );
          this.viewer.setStates(change.changed[key], false);
        }
        break;
    }
  },

  onCustomMessage: function (msg, buffers) {
    console.log(
      "New message with msgType:",
      msg.type,
      "msgId:",
      msg.id,
      ", object:",
      msg.object,
      ", name:",
      msg.name,
      ", args:",
      msg.args,
      ", type:",
      msg.threeType,
      ", update:",
      msg.update,
      ", buffers:",
      buffers
    );

    if (msg.object) var path = JSON.parse(msg.object);
    var objName = path.pop();

    var parent = null;
    try {
      parent = this;
      path.forEach((o) => (parent = parent[o]));
    } catch (error) {
      console.error(error);
    }
    console.log("parent:", parent, "object:", objName);

    var result = null;
    if (msg.name == null) {
      result = parent[objName];
    } else {
      var args = null;
      try {
        args = deserialize(msg.args);
        if (msg.threeType) {
          args = new THREE[msg.threeType](...args);
        }
      } catch (error) {
        console.error(error);
      }
      console.log("args:", args);

      try {
        if (msg.name === "=") {
          result = parent[objName] = args[0];
        } else {
          if (msg.threeType) {
            result = parent[objName][msg.name](args);
          } else {
            result = parent[objName][msg.name](...args);
          }
        }

        if (msg.update) {
          this.viewer.camera.updateProjectionMatrix();
          this.viewer.controls.update();
          this.viewer.update(true, false);
        }

        // const returnMsg = {
        //     type: 'cad_viewer_method_result',
        //     id: msg.id,
        //     result: serialize(result),
        // }

        // console.log("sending msg with id:", msg.id, "result:", result)

        // this.model.send(returnMsg, this.callbacks(), null);
      } catch (error) {
        console.log(error);
      }
    }
    try {
      this.model.set("result", serialize({ msg_id: msg.id, result: result }));
      this.model.save_changes();
    } catch (error) {
      console.log(error);
    }
  }
});
