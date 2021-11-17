from ._version import __version__

from IPython.display import display

from .widget import AnimationTrack, CadViewer
from .sidecar import (
    set_viewer,
    get_viewer,
    get_viewers,
    get_default,
    close_viewer,
    close_viewers,
    Viewer,
    ViewerSidecar,
)
from .utils import split_args


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


def show(shapes, states, sidecar=None, anchor="split-right", **kwargs):
    """
    Will handle sidecar before showing the CAD objects

    Parameters
    ----------
    shapes : dict
        Nested tessellated shapes
    states : dict
        State of the nested cad objects, key = object path, value = 2-dim tuple of 0/1 (hidden/visible) for
        object and edges
    sidecar : str, default None
        Title of a new or existing sidecar or None
    anchor : str, default split-right
        Where to open the sidecar: "right", "left", "split_top", "split_bottom", "split_right", "split_left"
    """

    create_args, add_shape_args = split_args(kwargs)

    if sidecar is None:
        scv = get_viewer()
        if scv is None:
            cv = CadViewer(**create_args)
            display(cv.widget)
            cv.add_shapes(shapes, states, **add_shape_args)
        else:
            if create_args:
                print(f"For an existing sidecar the create view arguments {create_args} are ignored")
            scv.show(shapes, states, **add_shape_args)
            cv = scv.viewer.view
    else:
        scv = get_viewer(sidecar)
        if scv is None:
            cv = CadViewer(**create_args)
            viewer = Viewer(cv.widget, cv.add_shapes, None, cv.dispose)
            scv = ViewerSidecar(sidecar, anchor=anchor)
            scv.attach(viewer)
        else:
            if create_args:
                print(f"For an existing sidecar the create view arguments {create_args} are ignored")

        scv.show(shapes, states, **add_shape_args)
        cv = scv.viewer.view
    return cv