import uuid
from ._version import __version__

from IPython.display import display, HTML

from .widget import AnimationTrack, CadViewer, get_viewer_by_id, get_viewers_by_id
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


MESSAGES = {
    "split-left": "split-left window",
    "split-right": "split-right window",
    "split-top": "split-top window",
    "split_bottom": "split-bottom window",
    "right": "sidecar window",
    None: "sidecar window",
}


def open_viewer(
    title=None,
    anchor="right",
    cad_width=800,
    tree_width=250,
    height=600,
    aspect_ratio=0.75,
    theme="browser",
    glass=True,
    tools=True,
    pinning=True,
    default=True,
):

    if cad_width is not None and cad_width < 780:
        cad_width = 780
        print("`cad_width` cannot be smaller than 780, setting to 780")

    id_ = str(uuid.uuid4())

    if title is None or title == "":
        viewer = CadViewer(
            title=None,
            anchor=None,
            cad_width=cad_width,
            tree_width=tree_width,
            height=height,
            theme=theme,
            glass=glass,
            tools=tools,
            pinning=pinning,
            id_=id_,
        )

        display(viewer.widget)

        image_id = f"img_{id_}"
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
                    aspect_ratio=aspect_ratio,
                    height=height,
                    theme=theme,
                    glass=glass,
                    tools=tools,
                    pinning=False,
                    id_=id_,
                )
                display(viewer.widget)
                error = None

            except Exception as ex:
                error = ex

        if error is None:
            out.resize_sidebar(cad_width + (0 if glass else tree_width) + 12)

            set_sidecar(title, viewer)
            if default:
                _set_default_sidecar(title)

    if error is None:
        viewer.register_viewer()
        return viewer
    else:
        raise RuntimeError(error)


def show(
    shapes,
    tracks=None,
    #
    # Viewer options
    title=None,
    anchor=None,
    cad_width=None,
    tree_width=None,
    aspect_ratio=None,
    height=None,
    theme=None,
    glass=None,
    tools=None,
    pinning=None,
    new_tree_behavior=True,
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
    up=None,
    control=None,
    ortho=None,
    axes=None,
    axes0=None,
    grid=None,
    center_grid=None,
    explode=None,
    ticks=None,
    transparent=None,
    black_edges=None,
    collapse=None,
    reset_camera=None,
    clip_slider_0=None,
    clip_slider_1=None,
    clip_slider_2=None,
    clip_normal_0=None,
    clip_normal_1=None,
    clip_normal_2=None,
    clip_intersection=None,
    clip_planes=None,
    clip_object_colors=None,
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

    Valid keywords:

    - UI
        glass:             Use glass mode where tree is an overlay over the cad object (default=True)
        tools:             Show tools (default=True)
        cad_width:         Width of the cad canvas (default=800)
        height:            Height of the cad canvas (default=600)
        tree_width:        Width of the object tree (default=240)
        theme:             Theme "light" or "dark" (default="light")
        pinning:           Allow replacing the CAD View by a canvas screenshot (default=True in cells, else False)
        new_tree_behavior: Whether to  hide the complete shape when clicking on the eye (True, default) or only
                           the faces (False)

    - Viewer
        axes:              Show axes (default=False)
        axes0:             Show axes at (0,0,0) (default=False)
        grid:              Show grid (default=False)
        ortho:             Use orthographic projections (default=True)
        transparent:       Show objects transparent (default=False)
        default_opacity:   Opacity value for transparent objects (default=0.5)
        black_edges:       Show edges in black color (default=False)
        control:           Mouse control use "orbit" control instead of "trackball" control (default="trackball")
        collapse:          "1": collapse all single leaf nodes,
                           "R": expand root only,
                           "C": collapse all nodes,
                           "E"": expand all nodes
                           (default="R"")
        ticks:             Hint for the number of ticks in both directions (default=10)
        center_grid:       Center the grid at the origin or center of mass (default=False)
        up:                Use z-axis ('Z') or y-axis ('Y') as up direction for the camera (default="Z")
        explode:           Turn on explode mode (default=False)

        zoom:              Zoom factor of view (default=1.0)
        position:          Camera position
        quaternion:        Camera orientation as quaternion
        target:            Camera look at target
        reset_camera:      Camera.RESET: Reset camera position, rotation, zoom and target
                           Camera.CENTER: Keep camera position, rotation, zoom, but look at center
                           Camera.KEEP: Keep camera position, rotation, zoom, and target
                           (default=Camera.RESET)
        clip_slider_0:     Setting of clipping slider 0 (default=None)
        clip_slider_1:     Setting of clipping slider 1 (default=None)
        clip_slider_2:     Setting of clipping slider 2 (default=None)
        clip_normal_0:     Setting of clipping normal 0 (default=[-1,0,0])
        clip_normal_1:     Setting of clipping normal 1 (default=[0,-1,0])
        clip_normal_2:     Setting of clipping normal 2 (default=[0,0,-1])
        clip_intersection: Use clipping intersection mode (default=[False])
        clip_planes:       Show clipping plane helpers (default=False)
        clip_object_colors: Use object color for clipping caps (default=False)

        pan_speed:         Speed of mouse panning (default=1)
        rotate_speed:      Speed of mouse rotate (default=1)
        zoom_speed:        Speed of mouse zoom (default=1)

    - Renderer
        default_edgecolor: Default mesh color (default=(128, 128, 128))
        ambient_intensity: Intensity of ambient light (default=1.00)
        direct_intensity:  Intensity of direct light (default=1.10)
        metalness:         Metalness property of the default material (default=0.30)
        roughness:         Roughness property of the default material (default=0.65)

    - Debug
        debug:             Show debug statements to the VS Code browser console (default=False)
        timeit:            Show timing information from level 0-3 (default=False)
    """

    viewer = None
    if title is not None:

        viewer = get_sidecar(title)
        if viewer is None:
            if anchor is None:
                anchor = "right"
        else:
            # clean the shapes so that the same object can be show several times
            viewer.widget.shapes = {}

            if anchor is not None and viewer.widget.anchor != anchor:
                warn(
                    f"Parameter 'anchor' cannot be changed after sidecar with title '{title}' has been openend"
                )
                anchor = viewer.widget.anchor
            if theme is not None and viewer.widget.theme != theme:
                warn(
                    f"Parameter 'theme' cannot be changed after sidecar with title '{title}' has been openend"
                )
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
            if key in (
                "position",
                "quaternion",
                "target",
                "zoom",
            ):
                return getattr(viewer.widget, key) if val is None else val
            else:
                return default if val is None else val

    kwargs = {}

    if viewer is None:
        kwargs["glass"] = preset("glass", glass, True)
        kwargs["tools"] = preset("tools", tools, True)
    else:
        kwargs["glass"] = preset("glass", glass, viewer.widget.glass)
        kwargs["tools"] = preset("tools", tools, viewer.widget.tools)

    kwargs["height"] = preset("height", height, 600)
    kwargs["cad_width"] = preset("cad_width", cad_width, 800)
    kwargs["tree_width"] = preset("tree_width", tree_width, 250)
    kwargs["aspect_ratio"] = preset("aspect_ratio", aspect_ratio, 0.75)

    kwargs["new_tree_behavior"] = preset("new_tree_behavior", new_tree_behavior, True)
    kwargs["theme"] = preset("theme", theme, "browser")
    kwargs["normal_len"] = preset("normal_len", normal_len, 0)
    kwargs["default_edgecolor"] = preset(
        "default_edgecolor", default_edgecolor, "#707070"
    )
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
    kwargs["center_grid"] = preset("grid", center_grid, False)
    kwargs["ticks"] = preset("ticks", ticks, 10)
    kwargs["explode"] = preset("explode", explode, False)
    kwargs["transparent"] = preset("transparent", transparent, False)
    kwargs["black_edges"] = preset("black_edges", black_edges, False)
    kwargs["collapse"] = preset("collapse", collapse, "R")
    kwargs["reset_camera"] = preset("reset_camera", reset_camera, "reset")
    kwargs["zoom_speed"] = preset("zoom_speed", zoom_speed, 0.5)
    kwargs["pan_speed"] = preset("pan_speed", pan_speed, 0.5)
    kwargs["rotate_speed"] = preset("rotate_speed", rotate_speed, 1.0)
    kwargs["timeit"] = preset("timeit", timeit, False)
    kwargs["debug"] = preset("debug", debug, False)
    if position is not None:
        kwargs["position"] = preset("position", position, None)
    if quaternion is not None:
        kwargs["quaternion"] = preset("quaternion", quaternion, None)
    if target is not None:
        kwargs["target"] = preset("target", target, None)
    if zoom is not None:
        kwargs["zoom"] = preset("zoom", zoom, None)
    kwargs["clip_slider_0"] = preset("clip_slider_0", clip_slider_0, None)
    kwargs["clip_slider_1"] = preset("clip_slider_1", clip_slider_1, None)
    kwargs["clip_slider_2"] = preset("clip_slider_2", clip_slider_2, None)
    kwargs["clip_normal_0"] = preset("clip_normal_0", clip_normal_0, [-1, 0, 0])
    kwargs["clip_normal_1"] = preset("clip_normal_1", clip_normal_1, [0, -1, 0])
    kwargs["clip_normal_2"] = preset("clip_normal_2", clip_normal_2, [0, 0, -1])
    kwargs["clip_intersection"] = preset("clip_intersection", clip_intersection, False)
    kwargs["clip_planes"] = preset("clip_planes", clip_planes, False)
    kwargs["clip_object_colors"] = preset(
        "clip_object_colors", clip_object_colors, False
    )

    if title is None:
        if get_default_sidecar() is None:
            viewer = open_viewer(
                title=None,
                anchor=None,
                pinning=True if pinning is None else pinning,
                **display_args(kwargs),
            )
        else:
            title = get_default_sidecar()
            viewer = get_sidecar(title)
            if viewer is None:
                viewer = open_viewer(
                    title=title,
                    anchor=None,
                    pinning=False if pinning is None else pinning,
                    **display_args(kwargs),
                )
    else:
        viewer = get_sidecar(title)
        if viewer is None:
            viewer = open_viewer(
                title=title, pinning=pinning, anchor=anchor, **display_args(kwargs)
            )
    # print(dict(sorted(viewer_args(kwargs).items())))
    viewer.add_shapes(shapes, tracks, **viewer_args(kwargs))
    return viewer


def set_default_sidecar(title, anchor="right"):
    _set_default_sidecar(title)
    if get_sidecar(title) is None:
        open_viewer(title, anchor=anchor)
