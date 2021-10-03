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
    this.ignoreNext = false;
  },

  notificationCallback(change) {
    this.ignoreNext = true; // change comes from python, so do not set traitlet back
    Object.keys(change).forEach((key) => {
      if (key === "camera_position" || key == "camera_zoom") {
        // remove the prefix to be compliant with traitlets
        this.model.set(key.slice(7), change[key]["new"]);
      } else {
        this.model.set(key, change[key]["new"]);
      }
    });
    this.ignoreNext = false;
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

    // Do not set traitlet if the change already comes from python
    if (this.ignoreNext) {
      return;
    }

    const key = Object.keys(change.changed)[0];
    console.log("handle_change", key);
    switch (key) {
      case "zoom":
        this.viewer.setCameraZoom(change.changed[key], false);
        break;
      case "position":
        this.viewer.setCameraPosition(change.changed[key], false, false);
        break;
      case "axes":
        this.viewer.setAxes(change.changed[key], false);
        break;
      case "grid":
        this.viewer.setGrids(...change.changed[key], false);
        break;
      case "axes0":
        this.viewer.setAxes0(change.changed[key], false);
        break;
      case "ortho":
        this.viewer.switchCamera(change.changed[key], false, false);
        break;
      case "transparent":
        this.viewer.setTransparent(change.changed[key], false);
        break;
      case "black_edges":
        this.viewer.setBlackEdges(change.changed[key], false);
        break;
      case "bb_factor":
        this.viewer.bb_factor = change.changed[key];
        break;
      case "tools":
        this.display.setTools(change.changed[key], false);
        break;
      case "edge_color":
        this.viewer.setEdgeColor(change.changed[key], false);
        break;
      case "ambient_intensity":
        this.viewer.setAmbientLight(change.changed[key], false);
        break;
      case "direct_intensity":
        this.viewer.setDirectLight(change.changed[key], false);
        break;
      case "zoom_speed":
        this.viewer.setZoomSpeed(change.changed[key], false);
        break;
      case "pan_speed":
        this.viewer.setPanSpeed(change.changed[key], false);
        break;
      case "rotate_speed":
        this.viewer.setRotateSpeed(change.changed[key], false);
        break;
      case "states":
        this.viewer.setStates(change.changed[key], false);
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
