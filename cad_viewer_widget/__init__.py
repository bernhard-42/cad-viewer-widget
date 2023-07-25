import uuid
from ._version import __version__

from IPython.display import display, HTML

from .widget import AnimationTrack, CadViewer, Camera, Collapse
from .sidecar import Sidecar

from .sidecar import (
    get_sidecar,
    get_sidecars,
    set_sidecar,
    close_sidecars,
    close_sidecar,
    get_default as get_default_sidecar,
    set_default as _set_default_sidecar,
)

from .utils import display_args, viewer_args, warn


def _jupyter_labextension_paths():
    """
    Called by Jupyter Lab Server to detect if it is a valid labextension and
    to install the widget

    Returns
    =======
    src: Source directory name to copy files from. Webpack outputs generated files
        into this directory and Jupyter Lab copies from this directory during
        widget installation
    dest: Destination directory name to install widget files to. Jupyter Lab copies
        from `src` directory into <jupyter path>/labextensions/<dest> directory
        during widget installation
    """
    return [
        {
            "src": "labextension",
            "dest": "cad-viewer-widget",
        }
    ]


def _jupyter_nbextension_paths():
    """
    Called by Jupyter Notebook Server to detect if it is a valid nbextension and
    to install the widget

    Returns
    =======
    section: The section of the Jupyter Notebook Server to change.
        Must be 'notebook' for widget extensions
    src: Source directory name to copy files from. Webpack outputs generated files
        into this directory and Jupyter Notebook copies from this directory during
        widget installation
    dest: Destination directory name to install widget files to. Jupyter Notebook copies
        from `src` directory into <jupyter path>/nbextensions/<dest> directory
        during widget installation
    require: Path to importable AMD Javascript module inside the
        <jupyter path>/nbextensions/<dest> directory
    """
    return [
        {
            "section": "notebook",
            "src": "nbextension",
            "dest": "cad-viewer-widget",
            "require": "cad-viewer-widget/extension",
        }
    ]


def open_viewer(
    title=None,
    anchor="right",
    cad_width=800,
    tree_width=250,
    height=600,
    theme="browser",
    glass=False,
    tools=True,
    pinning=True,
):
    if title is None:
        viewer = CadViewer(
            title=title,
            anchor=anchor,
            cad_width=cad_width,
            tree_width=tree_width,
            height=height,
            theme=theme,
            glass=glass,
            tools=tools,
            pinning=pinning,
        )
        display(viewer.widget)

        image_id = "img_" + str(uuid.uuid4())
        html = "<div></div>"
        display(HTML(html), display_id=image_id)
        viewer.widget.image_id = image_id
        error = None
    else:
        out = Sidecar(title=title, anchor=anchor)
        with out:
            try:
                viewer = CadViewer(
                    title=title,
                    anchor=anchor,
                    cad_width=cad_width,
                    tree_width=tree_width,
                    height=height,
                    theme=theme,
                    glass=glass,
                    tools=tools,
                    pinning=False,
                )
                display(viewer.widget)
                error = None
            except Exception as ex:
                error = ex

        if error is None:
            out.resize_sidebar(cad_width + (0 if glass else tree_width) + 12)

            set_sidecar(title, viewer)
    if error is None:
        return viewer
    else:
        raise RuntimeError(error)


def show(
    shapes,
    states,
    tracks=None,
    #
    # Viewer options
    title=None,
    anchor=None,
    cad_width=None,
    tree_width=None,
    height=None,
    theme=None,
    glass=None,
    tools=None,
    pinning=None,
    #
    # render options
    normal_len=None,
    default_edgecolor=None,
    default_opacity=None,
    ambient_intensity=None,
    direct_intensity=None,
    metalness=None,
    roughness=None,
    #
    # add_shapes options
    control=None,
    up=None,
    ortho=None,
    axes=None,
    axes0=None,
    grid=None,
    explode=None,
    ticks=None,
    transparent=None,
    black_edges=None,
    collapse=None,
    reset_camera=None,
    position=None,
    quaternion=None,
    target=None,
    zoom=None,
    zoom_speed=None,
    pan_speed=None,
    rotate_speed=None,
    timeit=None,
    debug=None,
):
    """
    Show CAD objects in JupyterLab

    - shapes:            Serialized nested tessellated shapes
    - states:            State of the nested cad objects, key = object path, value = 2-dim tuple of 0/1 (hidden/visible) for object and edges

    Valid keywords:


    DISPLAY OPTIONS
    - title:              Name of the sidecar viewer (default=None)
    - anchor:             How to open sidecar: "right", "split-right", "split-bottom", ... (default="right")
    - cad_width:          Width of CAD view part of the view (default=800)
    - tree_width:         Width of navigation tree part of the view (default=250)
    - height:             Height of the CAD view (default=600)
    - theme:              Theme "light" or "dark" (default="light")
    - tools:              Show the viewer tools like the object tree (default=True)
    - glass:              Use the glass mode, i.e. CAD navigation as transparent overlay (default=False)
    - pinning:            Allow replacing the CAD View by a canvas screenshot (default=True in cells, else False)

    TESSELLATION OPTIONS
    - default_edgecolor: Default edge color (default="#707070")
    - default_opacity:    Default opacity (default=0.5)
    - ambient_intensity   Default ambient (default=1.0)
    - direct_intensity:   Default direct (default=1.1)
    - metalness : float:  The degree of material metalness (default 0.3)
    - roughness : float:  The degree of material roughness (default 0.65)
    - normal_len:         Render vertex normals if > 0 (default=0)
    - render_edges:       Render edges  (default=True)
    - render_mates:       Render mates (for MAssemblies, default=False)
    - mate_scale:         Scale of rendered mates (for MAssemblies, default=1)

    VIEWER OPTIONS
    - control:            Use trackball controls ('trackball') or orbit controls ('orbit') (default='trackball')
    - up:                 Camera up direction is Z or Y (default='Z')
    - ortho:              Use orthographic projections (default=True)
    - axes:               Show axes (default=False)
    - axes0:              Show axes at (0,0,0) (default=False)
    - grid:               Show grid (default=[False, False, False])
    - ticks:              Hint for the number of ticks in both directions (default=10)
    - explode:            Whether explode widget is visibe or not (default=False)
    - transparent:        Show objects transparent (default=False)
    - black_edges:        Show edges in black (default=False)
    - collapse:           Collapse CAD tree (1: collapse nodes with single leaf, 2: collapse all nodes, default=0)
    - reset_camera:       Whether to reset camera (True) or not (False) (default=True)
    - position:           Absolute camera position that will be scaled (default=None)
    - quaternion:         Camera rotation as quaternion (x, y, z, w) (default=None)
    - target:             Camera target to look at (default=None)
    - zoom:               Zoom factor of view (default=2.5)
    - reset_camera:       Reset camera position, rotation and zoom to default (default=True)
    - zoom_speed:         Mouse zoom speed (default=1.0)
    - pan_speed:          Mouse pan speed (default=1.0)
    - rotate_speed:       Mouse rotate speed (default=1.0)
    - timeit:             Show rendering times, levels = False, 0,1,2,3,4,5 (default=False)
    - debug:           Enable debug output in browser console (default=False)
    """

    viewer = None
    if title is not None:
        viewer = get_sidecar(title)
        if viewer is not None:
            if anchor is not None and viewer.widget.anchor != anchor:
                warn(f"Parameter 'anchor' cannot be changed after sidecar with title '{title}' has been openend")
                anchor = viewer.widget.anchor
            if theme is not None and viewer.widget.theme != theme:
                warn(f"Parameter 'theme' cannot be changed after sidecar with title '{title}' has been openend")
                theme = viewer.widget.theme
            if pinning:
                warn("Pinning not suported for sidecar views")
            if glass is not None and viewer.glass != glass:
                viewer.glass = glass
            if tools is not None and viewer.tools != tools:
                viewer.tools = tools

    def preset(key, val, default):
        if viewer is None or viewer.widget.shapes == {}:
            return default if val is None else val
        else:
            if key in ("position", "quaternion", "target", "zoom", "position0", "quaternion0", "target0", "zoom0"):
                return getattr(viewer.widget, key) if val is None else val
            else:
                return default if val is None else val

    kwargs = {}
    if title is not None and viewer is None:
        anchor = "right"
    if viewer is None:
        kwargs["glass"] = preset("glass", glass, False)
        kwargs["tools"] = preset("tools", tools, True)
    else:
        kwargs["glass"] = preset("glass", glass, viewer.widget.glass)
        kwargs["tools"] = preset("tools", tools, viewer.widget.tools)
    kwargs["cad_width"] = preset("cad_width", cad_width, 800)
    kwargs["tree_width"] = preset("tree_width", tree_width, 250)
    kwargs["height"] = preset("height", height, 600)
    kwargs["theme"] = preset("theme", theme, "browser")
    kwargs["normal_len"] = preset("normal_len", normal_len, 0)
    kwargs["default_edgecolor"] = preset("default_edgecolor", default_edgecolor, "#707070")
    kwargs["default_opacity"] = preset("default_opacity", default_opacity, 0.5)
    kwargs["ambient_intensity"] = preset("ambient_intensity", ambient_intensity, 1.0)
    kwargs["direct_intensity"] = preset("direct_intensity", direct_intensity, 1.1)
    kwargs["metalness"] = preset("metalness", metalness, 0.3)
    kwargs["roughness"] = preset("roughness", roughness, 0.65)
    kwargs["control"] = preset("control", control, "trackball")
    kwargs["up"] = preset("up", up, "Z")
    kwargs["ortho"] = preset("ortho", ortho, True)
    kwargs["axes"] = preset("axes", axes, False)
    kwargs["axes0"] = preset("axes0", axes0, False)
    kwargs["grid"] = preset("grid", grid, [False, False, False])
    kwargs["ticks"] = preset("ticks", ticks, 10)
    kwargs["explode"] = preset("explode", explode, False)
    kwargs["transparent"] = preset("transparent", transparent, False)
    kwargs["black_edges"] = preset("black_edges", black_edges, False)
    kwargs["collapse"] = preset("collapse", collapse, 0)
    kwargs["reset_camera"] = preset("reset_camera", reset_camera, Camera.RESET)
    kwargs["zoom_speed"] = preset("zoom_speed", zoom_speed, 0.5)
    kwargs["pan_speed"] = preset("pan_speed", pan_speed, 0.5)
    kwargs["rotate_speed"] = preset("rotate_speed", rotate_speed, 1.0)
    kwargs["timeit"] = preset("timeit", timeit, False)
    kwargs["debug"] = preset("debug", debug, False)
    if position is not None:
        kwargs["position"] = preset("position", position, False)
    if quaternion is not None:
        kwargs["quaternion"] = preset("quaternion", quaternion, False)
    if target is not None:
        kwargs["target"] = preset("target", target, False)
    if zoom is not None:
        kwargs["zoom"] = preset("zoom", zoom, False)

    if grid is None:
        grid = [False, False, False]

    if title is None:
        if get_default_sidecar() is None:
            viewer = open_viewer(
                title=None, anchor=None, pinning=True if pinning is None else pinning, **display_args(kwargs)
            )
        else:
            title = get_default_sidecar()
            viewer = get_sidecar(title)
            if viewer is None:
                viewer = open_viewer(
                    title=title, anchor=None, pinning=False if pinning is None else pinning, **display_args(kwargs)
                )
    else:
        viewer = get_sidecar(title)
        if viewer is None:
            viewer = open_viewer(title=title, pinning=pinning, anchor=anchor, **display_args(kwargs))

    viewer.add_shapes(shapes, states, tracks, **viewer_args(kwargs))
    return viewer


def set_default_sidecar(title, anchor="right"):
    _set_default_sidecar(title)
    if get_sidecar(title) is None:
        open_viewer(title, anchor=anchor)
