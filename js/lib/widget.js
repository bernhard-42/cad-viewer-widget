import { DOMWidgetModel, DOMWidgetView } from "@jupyter-widgets/base";

import { Viewer, Display, Timer, CollapseState } from "three-cad-viewer";

import { isTolEqual, length, normalize } from "./utils.js";
import { _module, _version } from "./version.js";

import "../style/index.css";

import App from "./app.js";

// Mapping of the Python collapse trait ("1"/"R"/"C"/"E") to the
// three-cad-viewer CollapseState enum, and back for notifications
const COLLAPSE_MAPPING = {
  1: CollapseState.LEAVES,
  R: CollapseState.ROOT,
  C: CollapseState.COLLAPSED,
  E: CollapseState.EXPANDED
};
const COLLAPSE_REVERSE_MAPPING = {
  [CollapseState.LEAVES]: "1",
  [CollapseState.ROOT]: "R",
  [CollapseState.COLLAPSED]: "C",
  [CollapseState.EXPANDED]: "E"
};

// Notification keys of three-cad-viewer that are forwarded to Python;
// each name must match a traitlet on CadViewerWidget. All other keys
// (e.g. zebra_*, studio_*, holroyd, selected) are ignored.
const NOTIFICATION_TRAITS = new Set([
  "position",
  "quaternion",
  "target",
  "zoom",
  "axes",
  "axes0",
  "grid",
  "ortho",
  "transparent",
  "black_edges",
  "tools",
  "glass",
  "tab",
  "center_grid",
  "explode",
  "states",
  "ambient_intensity",
  "direct_intensity",
  "metalness",
  "roughness",
  "default_edgecolor",
  "default_opacity",
  "zoom_speed",
  "pan_speed",
  "rotate_speed",
  "clip_intersection",
  "clip_planes",
  "clip_object_colors",
  "clip_slider_0",
  "clip_slider_1",
  "clip_slider_2",
  "clip_normal_0",
  "clip_normal_1",
  "clip_normal_2",
  "lastPick",
  "activeTool",
  "selectedShapeIDs",
  "zebra_count",
  "zebra_opacity",
  "zebra_direction",
  "zebra_color_scheme",
  "zebra_mapping_mode",
  "studio_environment",
  "studio_env_intensity",
  "studio_env_rotation",
  "studio_background",
  "studio_tone_mapping",
  "studio_exposure",
  "studio_shadow_intensity",
  "studio_shadow_softness",
  "studio_ao_intensity",
  "studio_texture_mapping",
  "studio_4k_env_maps"
]);

// Traits that map to a plain three-cad-viewer setter for runtime changes
const RUNTIME_SETTERS = {
  zebra_count: "setZebraCount",
  zebra_opacity: "setZebraOpacity",
  zebra_direction: "setZebraDirection",
  zebra_color_scheme: "setZebraColorScheme",
  zebra_mapping_mode: "setZebraMappingMode",
  studio_environment: "setStudioEnvironment",
  studio_env_intensity: "setStudioEnvIntensity",
  studio_env_rotation: "setStudioEnvRotation",
  studio_background: "setStudioBackground",
  studio_tone_mapping: "setStudioToneMapping",
  studio_exposure: "setStudioExposure",
  studio_shadow_intensity: "setStudioShadowIntensity",
  studio_shadow_softness: "setStudioShadowSoftness",
  studio_ao_intensity: "setStudioAOIntensity",
  studio_texture_mapping: "setStudioTextureMapping",
  studio_4k_env_maps: "setStudio4kEnvMaps"
};

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
      new_tree_behavior: null,
      keymap: null,

      // View traits

      shapes: null,
      states: null,
      state_updates: null,
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

      grid_font_size: null,
      zebra_count: null,
      zebra_opacity: null,
      zebra_direction: null,
      zebra_color_scheme: null,
      zebra_mapping_mode: null,
      studio_environment: null,
      studio_env_intensity: null,
      studio_env_rotation: null,
      studio_background: null,
      studio_tone_mapping: null,
      studio_exposure: null,
      studio_shadow_intensity: null,
      studio_shadow_softness: null,
      studio_ao_intensity: null,
      studio_texture_mapping: null,
      studio_4k_env_maps: null,

      // Generic UI traits

      tab: null,
      clip_intersection: null,
      clip_object_colors: null,
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
      activeTool: null,
      selectedShapeIDs: null,
      measure: null,

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
      for (const key of Object.keys(RUNTIME_SETTERS)) {
        this.model.on(`change:${key}`, this.handle_change, this);
      }

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
      newTreeBehavior: this.model.get("new_tree_behavior"),
      // three-cad-viewer >= 5 hides toolbar features unless explicitly enabled
      measureTools: true,
      selectTool: true,
      explodeTool: true,
      zebraTool: true,
      studioTool: true,
      zscaleTool: false,
      // measurements are computed by the Python backend, not the built-in mesh backend
      externalMeasurementBackend: true
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
      roughness: this.model.get("roughness")
    };
    this.debug("getRenderOptions", options);
    return options;
  }

  getViewerOptions() {
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
      new_tree_behavior: "newTreeBehavior",
      grid_font_size: "gridFontSize",
      zebra_count: "zebraCount",
      zebra_opacity: "zebraOpacity",
      zebra_direction: "zebraDirection",
      zebra_color_scheme: "zebraColorScheme",
      zebra_mapping_mode: "zebraMappingMode",
      studio_environment: "studioEnvironment",
      studio_env_intensity: "studioEnvIntensity",
      studio_env_rotation: "studioEnvRotation",
      studio_background: "studioBackground",
      studio_tone_mapping: "studioToneMapping",
      studio_exposure: "studioExposure",
      studio_shadow_intensity: "studioShadowIntensity",
      studio_shadow_softness: "studioShadowSoftness",
      studio_ao_intensity: "studioAOIntensity",
      studio_texture_mapping: "studioTextureMapping",
      studio_4k_env_maps: "studio4kEnvMaps"
    };
    var options = {};
    for (let key of Object.keys(optionsMapping)) {
      if (this.model.get(key) != null) {
        var jkey = optionsMapping[key];
        if (key == "grid") {
          options[jkey] = this.model.get(key).slice(); // clone the array to ensure changes get detected
        } else if (key == "collapse") {
          options[jkey] = COLLAPSE_MAPPING[this.model.get(key)];
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
      // ignore zero sized rects of hidden or not yet laid out containers,
      // else 0 gets stored in the model and propagated to resizeCadView
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

        this.model.set("cad_width", width);
        this.model.set("height", height);
        this.model.save_changes();
      }
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
      if (displayOptions.height == null && size.height > 60) {
        this.height = Math.round(size.height) - 60;
        displayOptions.height = this.height;
        this.model.set("height", this.height);
        this.model.save_changes();
      }
      if (displayOptions.height == null) {
        // container not laid out yet; use a sane default until the
        // ResizeObserver reports the real size
        displayOptions.height = 500;
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

    // Do not call display.glassMode/showTools here: since three-cad-viewer 5
    // the display is only wired to a viewer in setupUI (end of the Viewer
    // constructor), which applies glass and tools from the display options

    // Reuse the viewer across shows like ocp_vscode's viewer does: clear()
    // tears down the scene but keeps the WebGL context, viewer state and
    // studio environment cache alive, avoiding the flash of a full teardown
    if (this.viewer != null) {
      this.viewer.clear();
    } else {
      this.viewer = new Viewer(
        this.display,
        displayOptions,
        this.handleNotification.bind(this),
        null
      );
    }
  }

  handleNotification(change) {
    var changed = false;
    Object.keys(change).forEach((key) => {
      const new_value = change[key]["new"];
      if (key === "collapse") {
        // three-cad-viewer reports CollapseState numbers, the Python trait uses "1"/"R"/"C"/"E"
        const collapse = COLLAPSE_REVERSE_MAPPING[new_value];
        if (collapse != null) {
          this.model.set(key, collapse);
          changed = true;
          this.debug(`Setting Python attribute ${key} to`, collapse);
        }
      } else if (NOTIFICATION_TRAITS.has(key)) {
        this.model.set(key, new_value);
        changed = true;
        this.debug(`Setting Python attribute ${key} to`, new_value);
      } else {
        this.debug(`Ignoring notification for ${key}`, new_value);
      }
    });
    if (changed) {
      this.model.save_changes();
    }
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
    if (
      this.clipSettings.tab != null &&
      this.clipSettings.tab !== this.model.get("tab")
    ) {
      // only needed for embedding restore; the regular flow passes the tab
      // into render() via viewerOptions.tab
      this.viewer.setActiveTab(this.clipSettings.tab);
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

    // pass the raw {instances, shapes} data to three-cad-viewer, which
    // decodes the b64 buffers and instance refs natively (like ocp_vscode)
    this.shapes = this.model.get("shapes");

    const bbox = this.shapes["shapes"]["bb"];
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
    // whether an explicit zoom was provided with this call (the trait is set
    // on every add_shapes, so a non null value means the caller passed one)
    const newZoom = this.model.get("zoom") != null;

    this.tracks = [];

    var viewerOptions = this.getViewerOptions();
    if (this.model.get("tab") != null) {
      // render directly into the target tab to avoid a CAD-mode flicker
      viewerOptions.tab = this.model.get("tab");
      this.activeTab = viewerOptions.tab;
    }
    timer.split("viewer");

    // set the latest view dimension before rendering; the size properties are
    // read-only since three-cad-viewer 4, and resizeCadView cannot be called
    // before render(), hence write the state directly
    var cadWidth = this.model.get("cad_width");
    if (cadWidth == null) {
      cadWidth = this.width;
    }
    var height = this.model.get("height");
    if (height == null) {
      height = this.height;
    }
    if (cadWidth != null && cadWidth > 0) {
      this.viewer.state.set("cadWidth", cadWidth);
    }
    if (
      this.model.get("tree_width") != null &&
      this.model.get("tree_width") > 0
    ) {
      this.viewer.state.set("treeWidth", this.model.get("tree_width"));
    }
    if (height != null && height > 0) {
      this.viewer.state.set("height", height);
    }
    if (this.model.get("glass") != null) {
      this.viewer.state.set("glass", this.model.get("glass"));
    }

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
          const camera_distance = 2.5 * bb_radius;

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

    if (!newZoom && resetCamera === "keep" && this._camera_distance != null) {
      this.viewer.setCameraZoom(
        ((this._zoom == null ? 1.0 : this._zoom) *
          this.viewer.camera.camera_distance) /
          this._camera_distance
      );
    }

    this._position = this.viewer.getCameraPosition();
    this._quaternion = this.viewer.getCameraQuaternion();
    this._target = this.viewer.getCameraTarget();
    this._zoom = this.viewer.getCameraZoom();
    this._camera_distance = this.viewer.camera.camera_distance;

    this.clipping = {
      sliders: [
        this.viewer.getClipSlider(0),
        this.viewer.getClipSlider(1),
        this.viewer.getClipSlider(2)
      ],
      normals: [
        this.viewer.getClipNormal(0),
        this.viewer.getClipNormal(1),
        this.viewer.getClipNormal(2)
      ],
      planeHelpers: this.viewer.getClipPlaneHelpers(),
      objectColors: this.viewer.getObjectColorCaps(),
      intersection: this.viewer.getClipIntersection()
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
      this.viewer.setExplode(this.model.get("explode"));
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

  addTrack(track) {
    // dispatch the (selector, action, times, values) tuples from Python to the
    // typed track methods of three-cad-viewer >= 4
    const [selector, action, times, values] = track;
    switch (action) {
      case "t":
        this.viewer.addPositionTrack(selector, times, values);
        break;
      case "tx":
      case "ty":
      case "tz":
        this.viewer.addTranslationTrack(selector, action[1], times, values);
        break;
      case "q":
        this.viewer.addQuaternionTrack(selector, times, values);
        break;
      case "rx":
      case "ry":
      case "rz":
        this.viewer.addRotationTrack(selector, action[1], times, values);
        break;
      default:
        console.error(`cad-viewer-widget: unknown animation action ${action}`);
    }
  }

  addTracks(tracks) {
    this.tracks = tracks;
    if (Array.isArray(this.tracks) && this.tracks.length > 0) {
      for (var track of this.tracks) {
        this.addTrack(track);
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

    if (Object.prototype.hasOwnProperty.call(RUNTIME_SETTERS, key)) {
      if (this.viewer != null && change.changed[key] != null) {
        this.viewer[RUNTIME_SETTERS[key]](change.changed[key]);
      }
      return;
    }

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
        if (change.changed[key] != null) {
          this.viewer.setExplode(change.changed[key]);
        }
        break;
      case "collapse":
        var val = change.changed[key];
        if (["1", "R", "E", "C"].includes(val)) {
          this.viewer.collapseNodes(COLLAPSE_MAPPING[val]);
        }
        break;
      case "tools":
        setKey("getTools", "showTools", key);
        break;
      case "glass":
        flag = change.changed[key];
        this.viewer.glassMode(flag);
        break;
      case "cad_width":
        value = change.changed[key];
        if (value > 0) {
          this.viewer.resizeCadView(
            value,
            this.model.get("tree_width"),
            this.model.get("height"),
            this.model.get("glass")
          );
        }
        break;
      case "tree_width":
        value = change.changed[key];
        if (value > 0) {
          this.viewer.resizeCadView(
            this.model.get("cad_width"),
            value,
            this.model.get("height"),
            this.model.get("glass")
          );
        }
        break;
      case "height":
        value = change.changed[key];
        if (value > 0) {
          this.viewer.resizeCadView(
            this.model.get("cad_width"),
            this.model.get("tree_width"),
            value,
            this.model.get("glass")
          );
        }
        break;
      case "pinning":
        flag = change.changed[key];
        this.viewer.showPinning(flag);
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
        this.viewer.setStates(change.changed[key]);
        break;
      case "tab":
        value = change.changed[key];
        if (this.activeTab !== value) {
          this.activeTab = value;
          if (["tree", "clip", "material", "zebra", "studio"].includes(value)) {
            this.viewer.setActiveTab(value);
          } else {
            console.error(`cad-viewer-widget: unknown tab name ${value}`);
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
