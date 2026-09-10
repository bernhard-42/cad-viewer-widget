from ipywidgets import Output
from traitlets import Unicode, CaselessStrEnum, Integer


SIDECARS = {}
DEFAULT = None


class Sidecar(Output):
    _model_name = Unicode("CadViewerSidecarModel").tag(sync=True)
    _model_module = Unicode("cad-viewer-widget").tag(sync=True)
    _model_module_version = Unicode("4.1.0").tag(sync=True)
    _view_name = Unicode("CadViewerSidecarView").tag(sync=True)
    _view_module = Unicode("cad-viewer-widget").tag(sync=True)
    _view_module_version = Unicode("4.1.0").tag(sync=True)

    title = Unicode("CadViewer").tag(sync=True)
    anchor = CaselessStrEnum(
        [
            "split-right",
            "split-left",
            "split-top",
            "split-bottom",
            "tab-before",
            "tab-after",
            "right",
        ],
        default_value="right",
        allow_none=True,
    ).tag(sync=True)
    width = Integer(allow_none=True).tag(sync=True)

    def resize_sidebar(self, width):
        self.width = width


def set_sidecar(title, viewer):
    SIDECARS[title] = viewer


def _remove_sidecar(title):
    global DEFAULT  # pylint: disable=global-statement

    del SIDECARS[title]
    if DEFAULT == title:
        DEFAULT = None


def get_sidecar(title=None):
    if title is None:
        if DEFAULT is None:
            # print("No default viewer found")
            return
        else:
            title = DEFAULT

    sidecar = SIDECARS.get(title)
    if sidecar is None:
        # print(f'There is no viewer "{title}"')
        return

    if sidecar.disposed:
        _remove_sidecar(title)
        # print(f'There is no viewer "{title}"')
        return

    return sidecar


def get_sidecars():
    sidecars = {}
    deletions = []
    for title, viewer in SIDECARS.items():
        if viewer.disposed:
            deletions.append(title)
        else:
            sidecars[title] = viewer

    for title in deletions:
        _remove_sidecar(title)

    return sidecars


def get_default():
    return DEFAULT


def set_default(title):
    global DEFAULT  # pylint: disable=global-statement

    DEFAULT = title


def close_viewer_widgets(viewer):
    """Close a viewer's widgets and their comms, not only its Javascript.

    `viewer.close()` sets `disposed`, which is a message to the browser; the
    kernel-side widgets survive it, comms and all. Closing them here is what
    keeps a session flat: reopening a title used to leave the previous
    `Sidecar`, its `CadViewerWidget` and both `Layout`s alive - four widgets per
    call, measured as 4, 8, 12, 16 - and that comm churn is what makes the
    Jupyter server's ZMQ race likely, whose symptom is a cell stuck at `[*]`
    with an idle kernel.

    Every step is guarded: a half-built viewer must not stop the rest going.
    """
    try:
        viewer.close()  # the Javascript side disposes
    except Exception:  # noqa: BLE001  # pylint: disable=broad-except
        pass

    for widget in (getattr(viewer, "sidecar", None), getattr(viewer, "widget", None)):
        if widget is None:
            continue
        # The `Layout` goes too: a widget with a comm of its own, which
        # `Widget.close()` leaves open because layouts can be shared. These are
        # not - each was made for the widget being closed here.
        for w in (widget, getattr(widget, "layout", None)):
            if w is None:
                continue
            try:
                w.close()
            except Exception:  # noqa: BLE001  # pylint: disable=broad-except
                pass


def close_sidecars():
    global SIDECARS  # pylint: disable=global-statement
    global DEFAULT  # pylint: disable=global-statement

    for title, viewer in list(get_sidecars().items()):
        close_viewer_widgets(viewer)
        print(f'Closed viewer "{title}"')

    SIDECARS = {}
    DEFAULT = None


def close_sidecar(title):
    viewer = SIDECARS.get(title)
    if viewer is not None:
        close_viewer_widgets(viewer)
        # The entry went too far the other way before: the viewer was disposed
        # in the browser and left in `SIDECARS`, so `show(viewer=title)` still
        # found it and drew into a panel that was gone.
        _remove_sidecar(title)
        print(f'Closed viewer "{title}"')
