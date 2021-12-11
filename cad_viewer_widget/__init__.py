import uuid
from ._version import __version__

from IPython.display import display, HTML

from .widget import AnimationTrack, CadViewer
from .sidecar import Sidecar

from .sidecar import (
    get_sidecar,
    get_sidecars,
    set_sidecar,
    close_sidecars,
    close_sidecar,
    get_default,
    set_default as _set_default,
)

from .utils import display_args, viewer_args


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
    theme="light",
):
    if title is None:
        viewer = CadViewer(
            title=title,
            anchor=anchor,
            cad_width=cad_width,
            tree_width=tree_width,
            height=height,
            theme=theme,
            pinning=True,
        )
        display(viewer.widget)

        image_id = "img_" + str(uuid.uuid4())
        html = "<div></div>"
        display(HTML(html), display_id=image_id)
        viewer.widget.image_id = image_id

    else:

        out = Sidecar(title=title, anchor=anchor)
        with out:
            viewer = CadViewer(
                title=title,
                anchor=anchor,
                cad_width=cad_width,
                tree_width=tree_width,
                height=height,
                theme=theme,
                pinning=False,
            )
            display(viewer.widget)

        out.resizeSidebar(cad_width + tree_width + 12)

        set_sidecar(title, viewer)

    return viewer


def show(
    shapes,
    states,
    # Viewer options
    title=None,
    anchor="right",
    cad_width=800,
    tree_width=250,
    height=600,
    theme="light",
    tools=True,
    control="trackball",
    # add_shapes options
    ortho=True,
    axes=False,
    axes0=False,
    grid=None,
    ticks=10,
    transparent=False,
    black_edges=False,
    normal_len=0,
    default_edge_color="#707070",
    default_opacity=0.5,
    ambient_intensity=0.5,
    direct_intensity=0.3,
    reset_camera=True,
    zoom_speed=0.5,
    pan_speed=0.5,
    rotate_speed=1.0,
    timeit=False,
):
    kwargs = {
        "title": title,
        "anchor": anchor,
        "cad_width": cad_width,
        "tree_width": tree_width,
        "height": height,
        "theme": theme,
        "tools": tools,
        "control": control,
        "ortho": ortho,
        "axes": axes,
        "axes0": axes0,
        "grid": grid,
        "ticks": ticks,
        "transparent": transparent,
        "black_edges": black_edges,
        "normal_len": normal_len,
        "default_edge_color": default_edge_color,
        "default_opacity": default_opacity,
        "ambient_intensity": ambient_intensity,
        "direct_intensity": direct_intensity,
        "reset_camera": reset_camera,
        "zoom_speed": zoom_speed,
        "pan_speed": pan_speed,
        "rotate_speed": rotate_speed,
        "timeit": timeit,
    }

    if grid is None:
        grid = [False, False, False]

    if title is None:
        if get_default() is None:
            viewer = open_viewer(title=None, anchor=None, **display_args(kwargs))
        else:
            viewer = open_viewer(title=get_default(), anchor=None, **display_args(kwargs))
    else:
        viewer = get_sidecar(title)
        if viewer is None:
            viewer = open_viewer(title=title, anchor=anchor, **display_args(kwargs))

    viewer.add_shapes(shapes, states, **viewer_args(kwargs))
    return viewer


def set_default(title, anchor="right"):
    _set_default(title)
    if get_sidecar(title) is None:
        open_viewer(title, anchor=anchor)
