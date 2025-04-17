import { DOMWidgetModel, DOMWidgetView } from "@jupyter-widgets/base";

import { Viewer, Display, Timer } from "three-cad-viewer";

import { decode } from "./serializer.js";
import { isTolEqual, length, normalize } from "./utils.js";
import { _module, _version } from "./version.js";

import "../style/index.css";

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

      // Internal trait

      id: null,

      // Display traits

      title: null,
      anchor: null,
      cad_width: null,
      height: null,
      tree_width: null,
      aspect_ratio: null,
      theme: null,
      pinning: null,
      newTreeBehavior: null,

      // View traits

      shapes: null,
      states: null,
      tracks: null,
      timeit: null,
      tools: null,
      glass: null,

      ortho: null,
      control: null,
      up: null,
      axes: null,
      axes0: null,
      grid: null,
      center_grid: null,
      explode: null,
      ticks: null,
      transparent: null,
      black_edges: null,
      collapse: null,
      normal_len: null,

      default_edgecolor: null,
      default_opacity: null,
      ambient_intensity: null,
      direct_intensity: null,
      metalness: null,
      roughness: null,

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

      zoom_speed: null,
      pan_speed: null,
      rotate_speed: null,
      animation_speed: null,

      // Read only traitlets

      lastPick: null,

      initialize: null,
      image_id: null,

      result: "",
      debug: false,
      disposed: false,
      rendered: false
    };
  }
}

export class CadViewerView extends DOMWidgetView {
  initialize(...args) {
    super.initialize(...args);
    this.lastPosition = null;
    this.lastQuaternion = null;
    this.lastTarget = null;
    this.lastZoom = null;
    this.empty = true;
    this.activeTab = "";
    this.display = null;
    this.viewer = null;
  }

  debug(...args) {
    if (this._debug) {
      console.debug("cad-viewer-widget: ", ...args);
    }
  }

  render() {
    if (!this.model.rendered) {
      super.render();

      this.model.on("change:initialize", this.clearOrAddShapes, this);
      this.model.on("change:tracks", this.handle_change, this);
      this.model.on("change:position", this.handle_change, this);
      this.model.on("change:quaternion", this.handle_change, this);
      this.model.on("change:target", this.handle_change, this);
      this.model.on("change:zoom", this.handle_change, this);
      this.model.on("change:axes", this.handle_change, this);
      this.model.on("change:grid", this.handle_change, this);
      this.model.on("change:axes0", this.handle_change, this);
      this.model.on("change:ortho", this.handle_change, this);
      this.model.on("change:explode", this.handle_change, this);
      this.model.on("change:transparent", this.handle_change, this);
      this.model.on("change:black_edges", this.handle_change, this);
      this.model.on("change:collapse", this.handle_change, this);
      this.model.on("change:tools", this.handle_change, this);
      this.model.on("change:glass", this.handle_change, this);
      this.model.on("change:cad_width", this.handle_change, this);
      this.model.on("change:tree_width", this.handle_change, this);
      this.model.on("change:height", this.handle_change, this);
      this.model.on("change:pinning", this.handle_change, this);
      this.model.on("change:default_edgecolor", this.handle_change, this);
      this.model.on("change:default_opacity", this.handle_change, this);
      this.model.on("change:ambient_intensity", this.handle_change, this);
      this.model.on("change:direct_intensity", this.handle_change, this);
      this.model.on("change:metalness", this.handle_change, this);
      this.model.on("change:roughness", this.handle_change, this);
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
      this.model.on("change:debug", this.handle_change, this);
      this.model.on("change:disposed", this.handle_change, this);
      this.model.on("change:center_grid", this.handle_change, this);
      this.model.on("change:clip_object_colors", this.handle_change, this);
      this.model.on("change:measure", this.handle_change, this);

      this.listenTo(this.model, "msg:custom", this.onCustomMessage.bind(this));

      this.shell = App.getShell();

      // in case of embedding we need to state values later, since rendering resets them
      this.backupClipping();

      this.init = false;
      this.disposed = false;

      this.title = this.model.get("title");
      this.anchor = this.model.get("anchor");

      this.container = null;
      this.container_id = null;

      this.observer = null;

      this.height = null;
      this.width = null;

      // find and remove old cell viewers, e.g. when run the same cell
      App.cleanupCellViewers();

      // TODO: needed for embedding?
      // this.showViewer();

      // if (this.model.get("shapes") != "") {
      //   this.addShapes();
      // }

      this._position = null;
      this._quaternion = null;
      this._target = null;
      this._zoom = null;
      this._camera_distance = null;
      this._clipping = null;

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
      glass: this.model.get("glass"),
      tools: this.model.get("tools"),
      pinning: this.model.get("pinning"),
      keymap: this.model.get("keymap"),
      newTreeBehavior: this.model.get("new_tree_behavior")
    };
  }

  getRenderOptions() {
    var options = {
      normalLen: this.model.get("normal_len"),
      edgeColor: this.model.get("default_edgecolor"),
      defaultOpacity: this.model.get("default_opacity"),
      ambientIntensity: this.model.get("ambient_intensity"),
      directIntensity: this.model.get("direct_intensity"),
      metalness: this.model.get("metalness"),
      roughness: this.model.get("roughness"),
      measureTools: true
    };
    this.debug("getRenderOptions", options);
    return options;
  }

  getViewerOptions() {
    let collapseMapping = {
      1: 1,
      E: 0,
      C: 2,
      R: 3
    };

    const optionsMapping = {
      control: "control",
      up: "up",
      tools: "tools",
      glass: "glass",
      axes: "axes",
      axes0: "axes0",
      grid: "grid",
      ortho: "ortho",
      ticks: "ticks",
      collapse: "collapse",
      transparent: "transparent",
      black_edges: "blackEdges",
      timeit: "timeit",
      zoom_speed: "zoomSpeed",
      pan_speed: "panSpeed",
      rotate_speed: "rotateSpeed",
      center_grid: "centerGrid",
      clip_slider_0: "clipSlider0",
      clip_slider_1: "clipSlider1",
      clip_slider_2: "clipSlider2",
      clip_normal_0: "clipNormal0",
      clip_normal_1: "clipNormal1",
      clip_normal_2: "clipNormal2",
      clip_intersection: "clipIntersection",
      clip_planes: "clipPlaneHelpers",
      clip_object_colors: "clipObjectColors",
      new_tree_behavior: "newTreeBehavior"
    };
    var options = {
      measureTools: true
    };
    for (let key of Object.keys(optionsMapping)) {
      if (this.model.get(key) != null) {
        var jkey = optionsMapping[key];
        if (key == "grid") {
          options[jkey] = this.model.get(key).slice(); // clone the array to ensure changes get detected
        } else if (key == "collapse") {
          options[jkey] = collapseMapping[this.model.get(key)];
        } else {
          options[jkey] = this.model.get(key);
        }
      }
    }
    this.debug("getViewerOptions", options);
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

  resize = (rect) => {
    var width = Math.round(rect.width);
    var height = Math.round(rect.height);

    const displayOptions = this.getDisplayOptions();
    if (this.viewer && this.viewer.ready) {
      if (width > 0 && height > 0) {
        if (!displayOptions.glass) {
          width = width - displayOptions.treeWidth;
        }

        width = Math.max(780, width - 12);
        height = height - 60;
        const aspect_ratio = this.model.get("aspect_ratio");

        if (this.title != null && aspect_ratio > 0) {
          height = Math.round(Math.min(height, aspect_ratio * width));
          if (width < height) {
            height = Math.round(Math.min(height, aspect_ratio * width));
          } else {
            width = Math.round(
              Math.max(780, Math.min(width, height / aspect_ratio))
            );
          }
        }

        this.viewer.resizeCadView(
          width,
          displayOptions.treeWidth,
          height,
          displayOptions.glass
        );
      }

      this.model.set("cad_width", width);
      this.model.set("height", height);
      this.model.save_changes();
    }
  };

  showViewer() {
    const displayOptions = this.getDisplayOptions();
    this._debug = this.model.get("debug");

    if (this.display == null) {
      const container = document.createElement("div");
      container.id = `cvw_${Math.random().toString().slice(2)}`; // sufficient or uuid?
      container.innerHTML = "";

      this.container_id = container.id;
      this.container = container;

      if (this.title == null) {
        App.addCellViewer(container.id, this);
      } else {
        App.getSidecar(this.title).registerChild(this);
      }
      this.el.appendChild(container);

      let size = container.parentNode.parentNode.getBoundingClientRect();
      if (displayOptions.height == null) {
        this.height = Math.round(size.height) - 60;
        displayOptions.height = this.height;
        this.model.set("height", this.height);
        this.model.save_changes();
      }

      if (displayOptions.cadWidth < size.width && this.title != null) {
        // anchor != right
        this.width =
          Math.round(
            size.width - (displayOptions.glass ? 0 : displayOptions.treeWidth)
          ) - 12;
        displayOptions.cadWidth = this.width;
        this.model.set("cad_width", this.width);
        this.model.save_changes();
      }

      this.display = new Display(container, displayOptions);

      if (this.title != null) {
        // do not resize cell viewers
        this.observer = new ResizeObserver((entries) => {
          for (const entry of entries) {
            this.resize(entry.contentRect);
          }
        });

        this.observer.observe(container.parentNode.parentNode);
      }
    }

    this.display.glassMode(displayOptions.glass);
    this.display.showTools(displayOptions.tools);

    if (this.viewer != null) {
      this.clear();
    }

    this.viewer = new Viewer(
      this.display,
      displayOptions,
      this.handleNotification.bind(this),
      null
    );
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
    this.viewer.hasAnimationLoop = false;
    this.viewer.continueAnimation = false;
    this.viewer.dispose();
    this.viewer = null;
  }

  clearOrAddShapes() {
    this.init = this.model.get("initialize");

    if (this.init) {
      // support rest initial position and  keeping camera location
      if (!this.empty) {
        this.lastPosition = this.viewer.getCameraPosition();
        this.lastQuaternion = this.viewer.getCameraQuaternion();
        this.lastZoom = this.viewer.getCameraZoom();
        this.lastTarget = this.viewer.getCameraTarget();
      }
      this.showViewer();
    } else {
      this.addShapes();
      if (this.title != null) {
        this.resize(
          this.container.parentNode.parentNode.getBoundingClientRect()
        );
      }
    }
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

    this.shapes = { data: this.model.get("shapes") };
    decode(this.shapes);
    this.shapes = this.shapes["data"]["shapes"];

    const bbox = this.shapes["bb"];
    const center = [
      (bbox.xmax + bbox.xmin) / 2,
      (bbox.ymax + bbox.ymin) / 2,
      (bbox.zmax + bbox.zmin) / 2
    ];
    let bb_radius = Math.max(
      Math.sqrt(
        Math.pow(bbox.xmax - bbox.xmin, 2) +
          Math.pow(bbox.ymax - bbox.ymin, 2) +
          Math.pow(bbox.zmax - bbox.zmin, 2)
      ),
      length(center)
    );

    const timer = new Timer("addShapes", this.model.get("timeit"));

    const resetCamera = this.model.get("reset_camera");

    this.tracks = [];

    var viewerOptions = this.getViewerOptions();
    timer.split("viewer");

    // set the latest view dimension before rendering
    this.viewer.cadWidth = this.model.get("cad_width");
    if (this.viewer.cadWidth == null) {
      this.viewer.cadWidth = this.width;
    }
    this.viewer.treeWidth = this.model.get("tree_width");
    this.viewer.height = this.model.get("height");
    if (this.viewer.height == null) {
      this.viewer.height = this.height;
    }
    this.viewer.glass = this.model.get("glass");

    if (resetCamera === "reset") {
      // even if reset is requested, respect the position settings from the object

      if (this.model.get("zoom") !== undefined) {
        viewerOptions.zoom = this.model.get("zoom");
      }
      if (this.model.get("position") !== undefined) {
        viewerOptions.position = this.model.get("position");
      }
      if (this.model.get("quaternion") !== undefined) {
        viewerOptions.quaternion = this.model.get("quaternion");
      }
      if (this.model.get("target") !== undefined) {
        viewerOptions.target = this.model.get("target");
      }
      this._camera_distance = null;
    } else {
      if (this.model.get("position")) {
        viewerOptions.position = this.model.get("position");
      } else if (this._position) {
        if (resetCamera === "keep") {
          const camera_distance = 5 * bb_radius;

          var p = [0, 0, 0];
          for (var i = 0; i < 3; i++) {
            p[i] = this._position[i] - this._target[i];
          }
          p = normalize(p);
          var offset = resetCamera === "keep" ? this._target : [0, 0, 0];
          for (var i = 0; i < 3; i++) {
            p[i] = p[i] * camera_distance + offset[i];
          }
        } else {
          // center
          var p = [0, 0, 0];
          for (var i = 0; i < 3; i++) {
            p[i] = this._position[i] - this._target[i] + center[i];
          }
          this._target = center;
        }
      }
      viewerOptions.position = p;
      this._position = viewerOptions.position;

      if (this.model.get("quaternion")) {
        viewerOptions.quaternion = this.model.get("quaternion");
      } else if (this._quaternion) {
        viewerOptions.quaternion = this._quaternion;
      }

      if (this.model.get("target")) {
        viewerOptions.target = this.model.get("target");
      } else if (this._target) {
        viewerOptions.target = this._target;
      }

      if (this.model.get("zoom")) {
        viewerOptions.zoom = this.model.get("zoom");
      } else if (this._zoom) {
        viewerOptions.zoom = this._zoom;
      }
    }
    this.viewer.render(this.shapes, this.getRenderOptions(), viewerOptions);

    if (resetCamera === "keep" && this.camera_distance != null) {
      // console.log("camera_distance", this.camera_distance, viewer.camera.camera_distance, viewer.camera.camera_distance/this.camera_distance);
      viewer.setCameraZoom(
        ((this.zoom == null ? 1.0 : this.zoom) *
          viewer.camera.camera_distance) /
          this.camera_distance
      );
    }

    this._position = viewer.getCameraPosition();
    this._quaternion = viewer.getCameraQuaternion();
    this._target = viewer.controls.getTarget().toArray();
    this._zoom = viewer.getCameraZoom();
    this._camera_distance = viewer.camera.camera_distance;

    this.clipping = {
      sliders: [
        viewer.getClipSlider(0),
        viewer.getClipSlider(1),
        viewer.getClipSlider(2)
      ],
      normals: [
        viewer.getClipNormal(0),
        viewer.getClipNormal(1),
        viewer.getClipNormal(2)
      ],
      planeHelpers: viewer.getClipPlaneHelpers(),
      objectColors: viewer.getObjectColorCaps(),
      intersection: viewer.getClipIntersection()
    };

    timer.split("renderer");

    this.model.set("position", this._position);
    this.model.set("quaternion", this._quaternion);
    this.model.set("target", this._target);
    this.model.set("zoom", this._zoom);

    this.model.save_changes();

    this.setClipping();

    // add animation tracks if exist
    const tracks = this.model.get("tracks");
    if (tracks != "" && tracks != null) {
      this.addTracks(tracks);
      this.animate();
    }

    if (this.model.get("explode") != null) {
      let flag = this.model.get("explode");
      this.viewer.display.setExplode("", !flag); // workaround
      this.viewer.display.setExplode("", flag);
      this.viewer.display.setExplodeCheck(flag);
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
      if (this.viewer == null) return;

      const value = change.changed[key];
      const oldValue =
        arg == null ? this.viewer[getter]() : this.viewer[getter](arg);
      if (!isTolEqual(oldValue, value)) {
        this.debug(`Setting Javascript attribute ${key} to`, value);
        if (arg == null && arg2 == null) {
          this.viewer[setter](value, true);
        } else if (arg != null && arg2 != null) {
          this.viewer[setter](arg, value, arg2, true);
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
    var flag = null;
    this.debug("handle_change:", key, change.changed[key]);
    switch (key) {
      case "zoom":
        setKey("getCameraZoom", "setCameraZoom", key);
        this._zoom = this.viewer.getCameraZoom();
        break;
      case "position":
        setKey("getCameraPosition", "setCameraPosition", key, null, false);
        this._position = this.viewer.getCameraPosition();
        break;
      case "quaternion":
        setKey("getCameraQuaternion", "setCameraQuaternion", key);
        this._quaternion = this.viewer.getCameraQuaternion();
        break;
      case "target":
        setKey("getCameraTarget", "setCameraTarget", key);
        this._target = this.viewer.getCameraTarget();
        break;
      case "axes":
        setKey("getAxes", "setAxes", key);
        break;
      case "grid":
        setKey("getGrids", "setGrids", key);
        break;
      case "center_grid":
        this.viewer.setGridCenter(change.changed[key]);
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
      case "explode":
        if (this.model.get("explode") != null) {
          let flag = change.changed[key];
          this.viewer.display.setExplode("", flag);
          this.viewer.display.setExplodeCheck(!flag); // workaround
          this.viewer.display.setExplodeCheck(flag);
        }
        break;
      case "collapse":
        var val = change.changed[key];
        if (["1", "R", "E", "C"].includes(val)) {
          this.viewer.display.collapseNodes(val);
        }
        break;
      case "tools":
        setKey("getTools", "showTools", key);
        break;
      case "glass":
        flag = change.changed[key];
        this.viewer.display.glassMode(flag);
        break;
      case "cad_width":
        value = change.changed[key];
        this.viewer.resizeCadView(
          value,
          this.model.get("tree_width"),
          this.model.get("height"),
          this.model.get("glass")
        );
        break;
      case "tree_width":
        value = change.changed[key];
        this.viewer.resizeCadView(
          this.model.get("cad_width"),
          value,
          this.model.get("height"),
          this.model.get("glass")
        );
        break;
      case "height":
        value = change.changed[key];
        this.viewer.resizeCadView(
          this.model.get("cad_width"),
          this.model.get("tree_width"),
          value,
          this.model.get("glass")
        );
        break;
      case "pinning":
        flag = change.changed[key];
        this.viewer.display.showPinning(flag);
        break;
      case "default_edgecolor":
        setKey("getEdgeColor", "setEdgeColor", key);
        break;
      case "default_opacity":
        setKey("getOpacity", "setOpacity", key);
        break;
      case "ambient_intensity":
        setKey("getAmbientLight", "setAmbientLight", key, null, true);
        break;
      case "direct_intensity":
        setKey("getDirectLight", "setDirectLight", key, null, true);
        break;
      case "metalness":
        setKey("getMetalness", "setMetalness", key, null, true);
        break;
      case "roughness":
        setKey("getRoughness", "setRoughness", key, null, true);
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
      case "tracks":
        tracks = this.model.get("tracks");
        if (tracks == "") {
          this.clearAnimation();
        } else {
          this.addTracks(tracks);
        }
        break;
      case "state_updates":
        var states = change.changed[key];
        for (var k in states) {
          // supports leaves only. TODO: extend to full sub trees
          this.viewer.setState(k, states[k], false);
        }
        break;
      case "tab":
        value = change.changed[key];
        if (this.activeTab !== value) {
          this.activeTab = value;
          if (value === "tree" || value == "clip" || value == "material") {
            this.viewer.display.selectTabByName(value);
          } else {
            console.error(`cad-viewer-widget: unkonwn tab name ${value}`);
          }
        }
        break;
      case "clip_intersection":
        setKey("getClipIntersection", "setClipIntersection", key);
        break;
      case "clip_planes":
        setKey("getClipPlaneHelpers", "setClipPlaneHelpers", key);
        break;
      case "clip_normal_0":
        const slider_0 = this.viewer.getClipSlider(0);
        setKey("getClipNormal", "setClipNormal", key, 0, slider_0);
        break;
      case "clip_normal_1":
        const slider_1 = this.viewer.getClipSlider(1);
        setKey("getClipNormal", "setClipNormal", key, 1, slider_1);
        break;
      case "clip_normal_2":
        const slider_2 = this.viewer.getClipSlider(2);
        setKey("getClipNormal", "setClipNormal", key, 2, slider_2);
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
      case "clip_object_colors":
        this.viewer.setClipObjectColorCaps(change.changed[key]);
        break;
      case "debug":
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
      case "measure":
        this.viewer.handleBackendResponse(change.changed[key]);
        break;
    }
  }

  exportPng(filename, dataUrl) {
    if (filename == null) {
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
          filename: filename,
          src: dataUrl
        })
      );
      this.model.save_changes();
    }
  }

  saveAsPng(filename) {
    this.viewer.getImage(filename).then((result) => {
      this.exportPng(result.task, result.dataUrl);
    });
  }

  pinAsPng() {
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
    var path = msg.method;
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
      args = msg.args;
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
