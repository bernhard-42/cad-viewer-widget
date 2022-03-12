from ipywidgets import Output
from traitlets import Unicode, CaselessStrEnum, Integer


SIDECARS = {}
DEFAULT = None


class Sidecar(Output):
    _model_name = Unicode("CadViewerSidecarModel").tag(sync=True)
    _model_module = Unicode("cad-viewer-widget").tag(sync=True)
    _model_module_version = Unicode("1.1.1").tag(sync=True)
    _view_name = Unicode("CadViewerSidecarView").tag(sync=True)
    _view_module = Unicode("cad-viewer-widget").tag(sync=True)
    _view_module_version = Unicode("1.1.1").tag(sync=True)

    title = Unicode("CadViewer").tag(sync=True)
    anchor = CaselessStrEnum(
        ["split-right", "split-left", "split-top", "split-bottom", "tab-before", "tab-after", "right"],
        default_value="right",
        allow_none=True,
    ).tag(sync=True)
    width = Integer(allow_none=True).tag(sync=True)

    def resize_sidebar(self, width):
        self.width = width


def set_sidecar(title, viewer):
    SIDECARS[title] = viewer


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
        del SIDECARS[title]
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
        del SIDECARS[title]

    return sidecars


def get_default():
    return DEFAULT


def set_default(title):
    global DEFAULT  # pylint: disable=global-statement

    DEFAULT = title


def close_sidecars():
    global SIDECARS  # pylint: disable=global-statement
    global DEFAULT  # pylint: disable=global-statement

    for title, sidecar in get_sidecars().items():
        sidecar.close()
        print(f'Closed viewer "{title}"')

    SIDECARS = {}
    DEFAULT = None


def close_sidecar(title):
    sidecar = SIDECARS.get(title)
    if sidecar is not None:
        sidecar.close()
        print(f'Closed viewer "{title}"')
