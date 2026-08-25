import { DOMWidgetModel, DOMWidgetView } from "@jupyter-widgets/base";

import { Viewer, Display, Timer, CollapseState } from "three-cad-viewer";
import {
  addAnimationTrack,
  animate,
  applyConfig,
  buildDisplayOptions,
  createRenderer,
  currentValue,
  isApplicable
} from "ocp-viewer-core";

import { isTolEqual } from "./utils.js";
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
// This host's names on the left, the renderer's on the right. An ipywidgets
// traitlet is one name in both languages, so the config Python sends arrives in
// Python spelling and is translated here rather than on the way out - the rule
// is the same as every other client's, applied at the other end.
const TRAIT_TO_OPTION = {
    // Render options. These were a second table, inside the widget's own
    // a trait in neither is a setting the user can change that the renderer
    // never hears about.
    normal_len: "normalLen",
    default_edgecolor: "edgeColor",
    default_opacity: "defaultOpacity",
    ambient_intensity: "ambientIntensity",
    direct_intensity: "directIntensity",
    metalness: "metalness",
    roughness: "roughness",

    // Display options taken from the config rather than passed as geometry.
    modifier_keys: "keymap",
    theme: "theme",

    // Viewer options.
    orbit_control: "control",
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
    studio_4k_env_maps: "studio4kEnvMaps",

    // Camera, geometry and per-show control. None of these is picked up by
    // the three option builders - VIEWER_OPTION_KEYS names none of them - but
    // `traitsAsConfig` is also what the shared renderer and the shared setter
    // dispatch are handed, and both steer by exactly these. A trait absent
    // from this table is not read at all, which is the whole failure mode
    // this table exists to prevent.
    position: "position",
    quaternion: "quaternion",
    target: "target",
    zoom: "zoom",
    reset_camera: "resetCamera",
    explode: "explode",
    tab: "tab",
    analysis_tool: "analysisTool",
    cad_width: "cadWidth",
    tree_width: "treeWidth",
    height: "height"
  };
// The traits the shared dispatch can apply, derived rather than listed. A trait
// qualifies when the renderer option it maps to has a setter in the core, which
// `isApplicable` answers - so a setter added there arrives here without anyone
// remembering to add it, which is what the hand-written list this replaces kept
// failing to do: it held the zebra and studio families and nothing else,
// because they were simply the two added last.
const APPLIED_TRAITS = Object.keys(TRAIT_TO_OPTION).filter((trait) =>
  isApplicable(TRAIT_TO_OPTION[trait])
);

// Traits that are this widget's own business rather than viewer settings: the
// ipywidgets lifecycle, the animation tracks, and the two that carry a payload
// in from Python. These are the whole of what `handle_change` still switches on.
// The camera options, whose value the renderer also keeps in `_status`.
const CAMERA_OPTIONS = ["zoom", "position", "quaternion", "target"];

const HOST_TRAITS = [
  "tracks",
  "state_updates",
  "pinning",
  "debug",
  "disposed",
  "measure"
];

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
      modifier_keys: null,

      // View traits

      shapes: null,
      states: null,
      state_updates: null,
      tracks: null,
      timeit: null,
      tools: null,
      glass: null,

      ortho: null,
      orbit_control: null,
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
      analysis_tool: null,
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

      // Every other trait goes to the same handler, so the list is a loop over
      // the two that already say which traits exist: the ones the shared
      // dispatch can apply, and the ones this widget handles itself. Written
      // out, it was 44 lines that had to be remembered whenever a trait was
      // added - and `up`, `theme` and `reset_camera` show what happens when it
      // is not, since all three were declared, mapped, and heard by nobody.
      for (const key of [...APPLIED_TRAITS, ...HOST_TRAITS]) {
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

      // The viewer's own state, as the renderer reports it: what
      // `createRenderer` reads to carry a camera over and writes back after a
      // render. Held apart from the traits deliberately - `handleNotification`
      // writes the camera into the traits too, so a trait is both what the
      // caller asked for and what the viewer last did, and `keep` needs those
      // two to stay separate. One object, created once, because the renderer
      // captures it by reference.
      this._status = {};
      this._clipping = null;

      window.getCadViewers = App.getCadViewers;
      window.currentCadViewer = this;
      this.model.rendered = true;
    }
  }

  /**
   * The traits this widget holds, in the names the renderer knows them by.
   *
   * The one place this host's spelling is translated. Everything below works in
   * renderer names, as the shared code does.
   */
  traitsAsConfig() {
    const config = {};
    for (const trait of Object.keys(TRAIT_TO_OPTION)) {
      const value = this.model.get(trait);
      if (value == null) {
        continue;
      }
      if (trait === "grid") {
        // Cloned, or a change to the array is not detected as one
        config[TRAIT_TO_OPTION[trait]] = value.slice();
      } else if (trait === "collapse") {
        config[TRAIT_TO_OPTION[trait]] = COLLAPSE_MAPPING[value];
      } else if (trait === "orbit_control") {
        // A boolean in Python and a name in the renderer, so the mapping cannot
        // carry it - the same shape as collapse above. Python converted this on
        // the way in until the trait was called `control` and held the name
        // already; now the trait is the Python spelling and the conversion
        // belongs here, at the boundary, like every other one.
        config[TRAIT_TO_OPTION[trait]] = value ? "orbit" : "trackball";
      } else {
        config[TRAIT_TO_OPTION[trait]] = value;
      }
    }
    return config;
  }

  getDisplayOptions() {
    // The defaults are the core's; what is passed here is what this surface
    // differs on - a sidecar is sized by the caller, and it has the studio
    // tool where a panel does not.
    return buildDisplayOptions(this.traitsAsConfig(), {
      pinning: this.model.get("pinning"),
      measureTools: true,
      selectTool: true,
      explodeTool: true,
      zebraTool: true,
      studioTool: true,
      zscaleTool: false,
      // measurements are computed by the Python backend, not the built-in one
      externalMeasurementBackend: true
    }, {
      cadWidth: this.model.get("cad_width"),
      height: this.model.get("height"),
      treeWidth: this.model.get("tree_width")
    });
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

      // One renderer per viewer, as the page hosts build one per page. It
      // holds the previous render's camera distance, which the zoom
      // correction needs, so it must outlive a single show - built here in
      // the branch that creates the viewer, and not when one is reused.
      //
      // No `resize`: this host writes its dimensions into the viewer state
      // just before rendering, because its size properties are read-only and
      // `resizeCadView` cannot be called before the first render.
      this.renderer = createRenderer({
        viewer: this.viewer,
        status: this._status,
        overrides: {},
        sendStatus: () => this.publishCamera(),
        // Passed unconditionally: `debug()` decides at call time whether to
        // print, so capturing the flag here would freeze whatever it was when
        // the viewer was built.
        debug: (label, value) => this.debug(label, value)
      });
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
      } else if (key === "selected") {
        // A Select-tool selection lands in the system clipboard. The browser
        // holds the clipboard, and the selection click supplies the user
        // activation the clipboard API requires.
        if (Array.isArray(new_value) && new_value.length > 0) {
          navigator.clipboard?.writeText(new_value.join(",")).catch((error) => {
            console.warn("cad-viewer-widget: selection not copied to clipboard:", error);
          });
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

    const timer = new Timer("addShapes", this.model.get("timeit"));

    this.tracks = [];

    // The traits in the names the renderer knows them by. One config, and it
    // is what the shared renderer steers by: the camera keys, resetCamera,
    // the tab, and everything the option builders pick out of it.
    const config = this.traitsAsConfig();

    if (config.tab != null) {
      // Recorded before the render, which is where the tab is applied: the
      // scene is built in the target tab rather than painted in CAD mode and
      // switched.
      this.activeTab = config.tab;
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

    // Drawing the model and deciding where the camera ends up is the shared
    // policy: what `keep` means when the model underneath has changed, and
    // the zoom correction that goes with it. It reads and writes `_status`,
    // and calls `publishCamera` when it has settled.
    this.renderer.render(this.shapes, config);

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

    this.setClipping();

    // add animation tracks if exist
    const tracks = this.model.get("tracks");
    if (tracks != "" && tracks != null) {
      this.addTracks(tracks);
      this.animate();
    }

    // After the tracks, because `animate` turns explode off before it starts -
    // both transform the same objects. The shared renderer turns explode on
    // for a truthy config value; this is also what turns it off again, which
    // it deliberately does not do.
    if (this.model.get("explode") != null) {
      this.viewer.setExplode(this.model.get("explode"));
    }

    timer.stop();

    return true;
  }

  /**
   * Hand the camera the renderer settled on back to Python.
   *
   * `createRenderer`'s `sendStatus` hook: where the page hosts put a snapshot
   * on the wire, this host writes four traits and lets ipywidgets sync them.
   * Only the four - the rest of the status is the renderer's working state and
   * has no traitlet behind it.
   */
  publishCamera() {
    this.model.set("position", this._status.position);
    this.model.set("quaternion", this._status.quaternion);
    this.model.set("target", this._status.target);
    this.model.set("zoom", this._status.zoom);
    this.model.save_changes();
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
    addAnimationTrack(this.viewer, track, (action) =>
      console.error(`cad-viewer-widget: unknown animation action ${action}`)
    );
  }

  addTracks(tracks) {
    this.tracks = Array.isArray(tracks) ? tracks : [];
    for (const track of this.tracks) {
      this.addTrack(track);
    }
  }

  animate() {
    // Explode is turned off first, and the duration taken from the longest
    // track - both the shared answer, so that an animation runs the same
    // length here as in any other client.
    animate(this.viewer, this.tracks, this.model.get("animation_speed"), (action) =>
      console.error(`cad-viewer-widget: unknown animation action ${action}`)
    );
  }

  clearAnimation() {
    if (this.viewer.clipAction) {
      this.viewer.controlAnimation("stop");
    }
    this.viewer.clearAnimation();
    this.tracks = [];
  }

  handle_change(change) {
    const key = Object.keys(change.changed)[0];

    if (this.init) {
      this.debug("Ignore message");
      return;
    }

    const value = change.changed[key];
    this.debug("handle_change:", key, value);

    // This widget's own business first - lifecycle, animation, and the two
    // traits that carry a payload in from Python. Nothing here is a viewer
    // setting, so none of it belongs in the shared dispatch.
    switch (key) {
      case "debug":
        this._debug = value;
        return;
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
        return;
      case "tracks":
        if (this.model.get("tracks") == "") {
          this.clearAnimation();
        } else {
          this.addTracks(this.model.get("tracks"));
        }
        return;
      default:
        break;
    }

    if (this.viewer == null) {
      return;
    }

    switch (key) {
      case "state_updates":
        this.viewer.setStates(value);
        return;
      case "pinning":
        this.viewer.showPinning(value);
        return;
      case "measure":
        this.viewer.handleBackendResponse(value);
        return;
      default:
        break;
    }

    // Everything else is a viewer setting, and one dispatch applies all of
    // them. What used to be forty-odd cases reading a getter, comparing and
    // setting is the `accept` hook below; which setter each key becomes is the
    // core's answer, and no longer restated here.
    const option = TRAIT_TO_OPTION[key];
    if (option === undefined || value == null) {
      return;
    }

    // The two conversions the key mapping cannot carry, because they change the
    // value and not the name. Same pair `traitsAsConfig` handles.
    let converted = value;
    if (key === "collapse") {
      if (!["1", "R", "E", "C"].includes(value)) {
        return;
      }
      converted = COLLAPSE_MAPPING[value];
    } else if (key === "orbit_control") {
      converted = value ? "orbit" : "trackball";
    } else if (key === "tab") {
      // The tab notifies when it changes, which comes back as this trait - so
      // without a guard, setting it would answer itself for ever.
      if (this.activeTab === value) {
        return;
      }
      this.activeTab = value;
    }

    applyConfig(this.viewer, { [option]: converted }, {
      // Every setter that takes the flag gets `true`: a change that arrived
      // from Python has to be reported back, or the two halves drift.
      notify: true,

      // Only set what is not already set. `currentValue` is undefined for a key
      // the viewer cannot be asked - explode and the tab are actions rather
      // than state - and that reads as "apply it", which is what the cases
      // this replaces did for exactly those keys.
      accept: (optionKey, next) => {
        const current = currentValue(this.viewer, optionKey);
        return current === undefined || !isTolEqual(current, next);
      },

      // A viewport dimension is a resize, and only this host knows the other
      // two - it reads them from the traits, as each of the three cases did.
      resize: (optionKey, next) => {
        if (!(next > 0)) {
          return;
        }
        this.viewer.resizeCadView(
          optionKey === "cadWidth" ? next : this.model.get("cad_width"),
          optionKey === "treeWidth" ? next : this.model.get("tree_width"),
          optionKey === "height" ? next : this.model.get("height"),
          this.model.get("glass")
        );
      },

      onUnknown: (unknown) =>
        console.error(`cad-viewer-widget: no setter for '${unknown}' in ocp-viewer-core`)
    });

    // The camera keys keep the renderer's picture in step as well as the
    // viewer's: a camera moved from Python between two shows is what the next
    // `keep` carries over, and `createRenderer` reads that from `_status`.
    if (CAMERA_OPTIONS.includes(option)) {
      this._status[option] = currentValue(this.viewer, option);
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
