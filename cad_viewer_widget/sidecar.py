from ipywidgets import Output
from traitlets import Unicode, CaselessStrEnum, Integer


SIDECARS = {}
DEFAULT = None


class Sidecar(Output):
    _model_name = Unicode("CadViewerSidecarModel").tag(sync=True)
    _model_module = Unicode("cad-viewer-widget").tag(sync=True)
    _model_module_version = Unicode("4.1.3").tag(sync=True)
    _view_name = Unicode("CadViewerSidecarView").tag(sync=True)
    _view_module = Unicode("cad-viewer-widget").tag(sync=True)
    _view_module_version = Unicode("4.1.3").tag(sync=True)

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


# Viewers whose Javascript dispose has been asked for but whose kernel-side
# widgets are not closed yet. Closing a comm the browser still has a view on
# makes it send into nothing, which the kernel answers with `No such comm`. The
# dispose message and the comm close travel the same channel, so the browser
# sees them in order; what it does not have is time to act between them.
# Draining on the next call gives it that time without a timer or a thread, and
# bounds the wait to a burst rather than to a session.
#
# Measured over a `Run All`: closing unilaterally produced 84 stray messages,
# deferring by one call 6, and additionally waiting two seconds 4 - because the
# last few are the browser touching a stale view during a later render, which no
# delay prevents. So the wait is one call, not a clock: the remaining handful is
# harmless (ipykernel drops the message) and not worth holding every comm open
# for the length of a `Run All`.
_PENDING_CLOSE = []


def _close_widgets(viewer):
    """Close a viewer's widgets and their comms. Every step guarded: a
    half-built viewer must not stop the rest going."""
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


def drain_closed_viewers(force=False):
    """Close the widgets of viewers whose dispose has already been asked for.

    `force` is accepted so `close_sidecars` can say what it means; there is
    nothing left to defer to once a session's viewers are all going.
    """
    del force  # one call is the whole wait
    while _PENDING_CLOSE:
        _close_widgets(_PENDING_CLOSE.pop())


def close_viewer_widgets(viewer):
    """Dispose a viewer in the browser and close its widgets when it is safe.

    `viewer.close()` sets `disposed`, which is a message to the browser; the
    kernel-side widgets survive it, comms and all. Closing them is what keeps a
    session flat: reopening a title used to leave the previous `Sidecar`, its
    `CadViewerWidget` and both `Layout`s alive - four widgets per call, measured
    as 4, 8, 12, 16 - because `SIDECARS` only dropped the reference.

    The close is deferred by one call rather than done here: see `_PENDING_CLOSE`.
    """
    drain_closed_viewers()

    try:
        viewer.close()  # ask the browser to dispose
    except Exception:  # noqa: BLE001  # pylint: disable=broad-except
        pass

    _PENDING_CLOSE.append(viewer)


def close_sidecars():
    global SIDECARS  # pylint: disable=global-statement
    global DEFAULT  # pylint: disable=global-statement

    for title, viewer in list(get_sidecars().items()):
        close_viewer_widgets(viewer)
        print(f'Closed viewer "{title}"')

    # Nothing is coming after this, so there is nothing to wait for.
    drain_closed_viewers(force=True)

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
