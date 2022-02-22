import "../style/index.css";

import { DOMWidgetModel, DOMWidgetView } from "@jupyter-widgets/base";

import { Viewer, Timer } from "three-cad-viewer";

import { decode } from "./serializer.js";
import { isTolEqual } from "./utils.js";
import { _module, _version } from "./version.js";

import App from "./app.js";

export class CadViewerModel extends DOMWidgetModel {
  defaults() {
    return {
      ...super.defaults(),
      _model_name: "CadViewerModel",
      _model_module: _module,
      _model_module_version: _version,
      _view_name: "CadViewerView",
      _view_module: _module,
      _view_module_version: _version,

      // Display traits

      title: null,
      anchor: null,
      cadWidth: null,
      height: null,
      treeWidth: null,
      theme: null,
      pinning: null,

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

      default_edge_color: null,
      default_opacity: null,
      ambient_intensity: null,
      direct_intensity: null,

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

      reset_camera: true,

      position: null,
      quaternion: null,
      target: null,
      zoom: null,

      position0: null,
      quaternion0: null,
      target0: null,
      zoom0: null,

      zoom_speed: null,
      pan_speed: null,
      rotate_speed: null,
      animation_speed: null,

      // Read only traitlets

      lastPick: null,

      initialize: null,
      image_id: null,

      result: "",
      js_debug: false,
      disposed: false,
      rendered: false
    };
  }
}

export class CadViewerView extends DOMWidgetView {
  initialize(...args) {
    super.initialize(...args);
    this.position0 = null;
    this.quaternion0 = null;
    this.target0 = null;
    this.zoom0 = null;
    this.lastPosition = null;
    this.lastQuaternion = null;
    this.lastTarget = null;
    this.lastZoom = null;
    this.empty = true;
  }

  debug(...args) {
    if (this._debug) {
      console.debug("cad-viewer-widget: ", ...args);
    }
  }

  render() {
    if (!this.model.rendered) {
      super.render();

      this.model.on("change:tracks", this.handle_change, this);
      this.model.on("change:position", this.handle_change, this);
      this.model.on("change:quaternion", this.handle_change, this);
      this.model.on("change:target", this.handle_change, this);
      this.model.on("change:zoom", this.handle_change, this);
      this.model.on("change:axes", this.handle_change, this);
      this.model.on("change:grid", this.handle_change, this);
      this.model.on("change:axes0", this.handle_change, this);
      this.model.on("change:ortho", this.handle_change, this);
      this.model.on("change:transparent", this.handle_change, this);
      this.model.on("change:black_edges", this.handle_change, this);
      this.model.on("change:tools", this.handle_change, this);
      this.model.on("change:pinning", this.handle_change, this);
      this.model.on("change:default_edge_color", this.handle_change, this);
      this.model.on("change:default_opacity", this.handle_change, this);
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
      this.model.on("change:initialize", this.clearOrAddShapes, this);
      this.model.on("change:js_debug", this.handle_change, this);
      this.model.on("change:disposed", this.handle_change, this);

      this.listenTo(this.model, "msg:custom", this.onCustomMessage.bind(this));

      this.shell = App.getShell();

      // in case of embedding we need to state values later, since rendering resets them
      this.backupClipping();

      this.init = false;
      this.disposed = false;

      this.title = this.model.get("title");
      this.anchor = this.model.get("anchor");

      this.container_id = null;

      // find and remove old cell viewers, e.g. when run the same cell
      App.cleanupCellViewers();

      this.createDisplay();

      if (this.model.get("shapes") != "") {
        this.addShapes();
      }

      window.getCadViewers = App.getCadViewers;
      window.currentCadViewer = this;
      this.model.rendered = true;
    }
  }

  getDisplayOptions() {
    return {
      cadWidth: this.model.get("cad_width"),
      height: this.model.get("height"),
      treeWidth: this.model.get("tree_width"),
      theme: this.model.get("theme"),
      pinning: this.model.get("pinning")
    };
  }

  getRenderOptions() {
    return {
      normalLen: this.model.get("normal_len"),
      edgeColor: this.model.get("default_edge_color"),
      defaultOpacity: this.model.get("default_opacity"),
      ambientIntensity: this.model.get("ambient_intensity"),
      directIntensity: this.model.get("direct_intensity")
    };
  }

  getViewerOptions() {
    var options = {
      control: this.model.get("control"),
      tools: this.model.get("tools"),
      axes: this.model.get("axes"),
      axes0: this.model.get("axes0"),
      grid: this.model.get("grid").slice(), // clone the array to ensure changes get detected
      ortho: this.model.get("ortho"),
      ticks: this.model.get("ticks"),
      transparent: this.model.get("transparent"),
      blackEdges: this.model.get("black_edges"),
      timeit: this.model.get("timeit"),
      zoomSpeed: this.model.get("zoom_speed"),
      panSpeed: this.model.get("pan_speed"),
      rotateSpeed: this.model.get("rotate_speed"),
      position: this.model.get("position"),
      quaternion: this.model.get("quaternion"),
      target: this.model.get("target"),
      zoom: this.model.get("zoom")
    };

    return options;
  }

  dispose() {
    if (!this.disposed) {
      this.viewer.dispose();

      // first set disposed to true to avoid double dispose call
      this.disposed = true;

      // then set model widget, to block additional triggered dispose call
      this.model.set("disposed", true);
      this.model.save_changes();
    }
  }

  _barHandler(index, tab) {
    if (this.title === tab.title.label) {
      this.shell._rightHandler.sideBar.tabCloseRequested.disconnect(
        this._barHandler,
        this
      );

      // this will trigger dispose()
      this.widget.title.owner.dispose();
    }
  }

  createDisplay() {
    const options = this.getDisplayOptions();

    const container = document.createElement("div");
    container.id = `cvw_${Math.random().toString().slice(2)}`; // sufficient or uuid?
    this.container_id = container.id;

    if (this.title == null) {
      App.addCellViewer(container.id, this);
    } else {
      App.getSidecar(this.title).registerChild(this);
    }

    this.el.appendChild(container);

    this.viewer = new Viewer(
      container,
      options,
      this.handleNotification.bind(this),
      this.exportPng.bind(this),
      true
    );

    this.viewer.display.setAnimationControl(false);
    this.viewer.display.setTools(options.tools);
  }

  handleNotification(change) {
    Object.keys(change).forEach((key) => {
      const new_value = change[key]["new"];
      this.model.set(key, new_value);
      this.debug(`Setting Python attribute ${key} to`, new_value);
    });
    this.model.save_changes();
  }

  clear() {
    this.viewer.clear();
  }

  clearOrAddShapes() {
    this.init = this.model.get("initialize");

    if (this.init) {
      // support rest initial position and  keeping camera location
      if (!this.empty) {
        this.position0 = this.model.get("position0");
        this.quaternion0 = this.model.get("quaternion0");
        this.zoom0 = this.model.get("zoom0");
        this.target0 = this.model.get("target0");

        this.lastPosition = this.viewer.getCameraPosition();
        this.lastQuaternion = this.viewer.getCameraQuaternion();
        this.lastZoom = this.viewer.getCameraZoom();
        this.lastTarget = this.viewer.getCameraTarget();
      }
      this.clear();
    } else {
      const states = this.model.get("states");
      if (Object.keys(states).length > 0) {
        this.addShapes();
      }
    }
  }

  clone_states() {
    const states = this.model.get("states");
    const states2 = {};
    for (var key in states) {
      states2[key] = states[key].slice();
    }
    return states2;
  }

  backupClipping() {
    this.clipSettings = {
      tab: this.model.get("tab"),
      clip_planes: this.model.get("clip_planes"),
      clip_intersection: this.model.get("clip_intersection"),
      clip_normal_0: this.model.get("clip_normal_0"),
      clip_normal_1: this.model.get("clip_normal_1"),
      clip_normal_2: this.model.get("clip_normal_2"),
      clip_slider_0: this.model.get("clip_slider_0"),
      clip_slider_1: this.model.get("clip_slider_1"),
      clip_slider_2: this.model.get("clip_slider_2")
    };
  }

  setClipping() {
    if (this.clipSettings.tab != null) {
      this.viewer.display.selectTabByName(this.clipSettings.tab);
    }
    if (this.clipSettings.clip_intersection != null) {
      this.viewer.setClipIntersection(
        this.clipSettings.clip_intersection,
        false
      );
    }
    if (this.clipSettings.clip_planes != null) {
      this.viewer.setClipPlaneHelpers(this.clipSettings.clip_planes, false);
    }
    if (this.clipSettings.clip_normal_0 != null) {
      this.viewer.setClipNormal(0, this.clipSettings.clip_normal_0, false);
    }
    if (this.clipSettings.clip_normal_1 != null) {
      this.viewer.setClipNormal(1, this.clipSettings.clip_normal_1, false);
    }
    if (this.clipSettings.clip_normal_2 != null) {
      this.viewer.setClipNormal(2, this.clipSettings.clip_normal_2, false);
    }
    if (this.clipSettings.clip_slider_0 != null) {
      this.viewer.setClipSlider(0, this.clipSettings.clip_slider_0, false);
    }
    if (this.clipSettings.clip_slider_1 != null) {
      this.viewer.setClipSlider(1, this.clipSettings.clip_slider_1, false);
    }
    if (this.clipSettings.clip_slider_2 != null) {
      this.viewer.setClipSlider(2, this.clipSettings.clip_slider_2, false);
    }
  }

  addShapes() {
    if (this.model.get("initialize") == null) {
      return;
    }

    this.shapes = this.model.get("shapes");
    decode(this.shapes);
    this.states = this.clone_states();

    const timer = new Timer("addShapes", this.model.get("timeit"));
    this._debug = this.model.get("js_debug");

    const resetCamera = this.model.get("reset_camera");
    var position = null;
    var quaternion = null;
    var target = null;
    var zoom = null;

    this.tracks = [];

    var viewerOptions = this.getViewerOptions();

    timer.split("viewer");
    this.viewer.render(
      ...this.viewer.renderTessellatedShapes(
        this.shapes,
        this.states,
        this.getRenderOptions()
      ),
      this.states,
      viewerOptions
    );

    timer.split("renderer");

    if (this.empty || resetCamera) {
      // store inital camera location
      position = this.viewer.getCameraPosition();
      quaternion = this.viewer.getCameraQuaternion();
      target = this.viewer.getCameraTarget();
      zoom = this.viewer.getCameraZoom();

      this.empty = false;
    } else {
      this.viewer.setResetLocation(
        this.target0,
        this.position0,
        this.quaternion0,
        this.zoom0
      );

      position = [...this.lastPosition];
      quaternion = [...this.lastQuaternion];
      target = [...this.lastTarget];
      zoom = this.lastZoom;
      this.viewer.setCameraLocationSettings(
        this.lastPosition,
        this.lastQuaternion,
        this.lastTarget,
        this.lastZoom
      );
    }

    this.model.set("position", position);
    this.model.set("quaternion", quaternion);
    this.model.set("target", target);
    this.model.set("zoom", zoom);

    this.model.save_changes();

    this.setClipping();

    // add animation tracks if exist
    const tracks = this.model.get("tracks");
    if (tracks != "" && tracks != null) {
      this.addTracks(tracks);
      this.animate();
    }

    timer.stop();

    return true;
  }

  updateCamera() {
    var zoom = this.viewer.getCameraZoom();
    var position = this.viewer.getCameraPosition();
    var quaternion = this.viewer.getCameraQuaternion();
    var target = this.viewer.getCameraTarget();

    this.model.set("zoom", zoom);
    this.model.set("position", position);
    this.model.set("quaternion", quaternion);
    this.model.set("target", target);
  }

  addTracks(tracks) {
    this.tracks = tracks;
    if (Array.isArray(this.tracks) && this.tracks.length > 0) {
      for (var track of this.tracks) {
        this.viewer.addAnimationTrack(...track);
      }
    }
  }

  animate() {
    const speed = this.model.get("animation_speed");
    const duration = Math.max(
      ...this.tracks.map((track) => Math.max(...track[2]))
    );
    if (speed > 0) {
      this.viewer.initAnimation(duration, speed);
    }
  }

  clearAnimation() {
    if (this.viewer.clipAction) {
      this.viewer.controlAnimation("stop");
    }
    this.viewer.clearAnimation();
    this.tracks = [];
  }

  handle_change(change) {
    const setKey = (getter, setter, key, arg = null, arg2 = null) => {
      const value = change.changed[key];
      const oldValue =
        arg == null ? this.viewer[getter]() : this.viewer[getter](arg);
      if (!isTolEqual(oldValue, value)) {
        this.debug(`Setting Javascript attribute ${key} to`, value);
        if (arg == null && arg2 == null) {
          this.viewer[setter](value, true);
        } else if (arg != null) {
          this.viewer[setter](arg, value, true);
        } else if (arg2 != null) {
          this.viewer[setter](value, arg2, true);
        }
      }
    };

    const key = Object.keys(change.changed)[0];

    if (this.init) {
      this.debug("Ignore message");
      return;
    }

    var tracks = "";
    var value = null;

    switch (key) {
      case "zoom":
        setKey("getCameraZoom", "setCameraZoom", key);
        break;
      case "position":
        setKey("getCameraPosition", "setCameraPosition", key, null, false);
        break;
      case "quaternion":
        setKey("getCameraQuaternion", "setCameraQuaternion", key);
        break;
      case "target":
        setKey("getCameraTarget", "setCameraTarget", key);
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
      case "pinning":
        var flag = change.changed[key];
        this.viewer.display.setPinning(flag);
        break;
      case "default_edge_color":
        setKey("getEdgeColor", "setEdgeColor", key);
        break;
      case "default_opacity":
        setKey("getOpacity", "setOpacity", key);
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
        this._debug = change.changed[key];
        break;
      case "disposed":
        if (this.title != null) {
          const sidecar = App.getSidecar(this.title);
          if (sidecar != null) {
            if (this.anchor == "right") {
              sidecar.disposeSidebar(null, sidecar.widget);
            } else {
              sidecar.widget.title.owner.dispose();
            }
          }
        } else {
          this.dispose();
        }
        break;
    }
  }

  exportPng(image) {
    if (this.png_filename == null) {
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

      this.dispose();
      App.removeCellViewer(this.container_id);
    } else {
      this.model.set(
        "result",
        JSON.stringify({
          filename: this.png_filename,
          src: image.src
        })
      );
      this.model.save_changes();
      this.png_filename = null;
    }
  }

  saveAsPng(filename) {
    this.png_filename = filename;
    this.viewer.pinAsPng();
  }

  pinAsPng() {
    this.png_filename = null;
    this.viewer.pinAsPng();
  }

  onCustomMessage(msg, buffers) {
    this.debug(
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

    var object = this;
    var path = JSON.parse(msg.method);
    var method = path.pop();

    try {
      path.forEach((o) => (object = object[o]));
      this.debug("object:", object, "method:", method);
    } catch (error) {
      console.error(error);
      return;
    }

    var args = null;
    try {
      args = JSON.parse(msg.args);
      this.debug("args:", args);
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
      this.debug("method executed, result: ", result);
    } catch (error) {
      console.log(error);
    }
  }
}
