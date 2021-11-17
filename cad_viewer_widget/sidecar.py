from IPython.display import display
from sidecar import Sidecar

SIDECARS = {}
DEFAULT = None


class Viewer:
    def __init__(self, view, show, clean=None, close=None):
        self.view = view
        self._show = show
        self._clean = clean
        self._close = close

    def show(self, *args, **kwargs):
        self._show(*args, **kwargs)

    def clean(self):
        if self._clean is not None:
            self._clean()

    def close(self):
        if self._close is not None:
            self._close()


class ViewerSidecar:
    def __init__(self, title, anchor="split-right"):
        sc = Sidecar(title=title, anchor=anchor)
        SIDECARS[title] = self

        self.title = title
        self.sidecar = sc
        self.viewer = None

    def attach(self, viewer):
        self.viewer = viewer
        with self.sidecar:
            display(viewer.view)

    def clean(self, sidecar=False):
        if self.viewer:
            self.viewer.clean()

        if sidecar:
            self.sidecar.outputs = ()

    def close(self):
        global DEFAULT

        if self.viewer:
            self.viewer.close()

        self.sidecar.close()

        if SIDECARS.get(self.title) is not None:
            del SIDECARS[self.title]

        if DEFAULT == self.title:
            DEFAULT = None

    def show(self, *args, **kwargs):
        if self.viewer is None:
            raise ValueError("viewer needs to be attached")
        else:
            self.viewer.show(*args, **kwargs)


def get_viewer(title=None):
    if title is None:
        return SIDECARS.get(DEFAULT)
    else:
        return SIDECARS.get(title)


def get_viewers():
    return SIDECARS


def get_default():
    return DEFAULT


def set_viewer(title, anchor="split-right"):
    global DEFAULT

    DEFAULT = title
    if get_viewer(title) is None:
        SIDECARS[title] = ViewerSidecar(title, anchor=anchor)


def close_viewers():
    global SIDECARS
    global DEFAULT

    Sidecar.close_all()
    SIDECARS = {}
    DEFAULT = None


def close_viewer(title):
    global DEFAULT
    global SIDECARS

    scv = SIDECARS.get(title)
    if scv is not None:
        scv.close(sidecar=True)
