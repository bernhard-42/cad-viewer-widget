import uuid

from IPython.display import display, HTML
from ipywidgets import Output
from traitlets import Unicode, CaselessStrEnum, Integer

from .widget import CadViewer

SIDECARS = {}
DEFAULT = None

class Sidecar(Output):
    _model_name = Unicode("CadViewerSidecarModel").tag(sync=True)
    _model_module = Unicode("cad-viewer-widget").tag(sync=True)
    _model_module_version = Unicode("0.9.10").tag(sync=True)
    _view_name = Unicode("CadViewerSidecarView").tag(sync=True)
    _view_module = Unicode("cad-viewer-widget").tag(sync=True)
    _view_module_version = Unicode("0.9.10").tag(sync=True)

    title = Unicode('CadViewer').tag(sync=True)
    anchor = CaselessStrEnum(
        ['split-right', 'split-left', 'split-top', 'split-bottom', 'tab-before', 'tab-after', 'right'],
        default_value='right', 
        allow_none=True
    ).tag(sync=True)
    width = Integer(allow_none=True).tag(sync=True)

    def resizeSidebar(self, width):
        self.width = width


def open_viewer(title=None, anchor="right", cad_width=800, tree_width=250, height=600, **kwargs):
    if title is None:
        kwargs["pinning"] = True

        cv = CadViewer(**kwargs)
        display(cv.widget)

        image_id = "img_" + str(uuid.uuid4())
        html = "<div></div>"
        display(HTML(html), display_id=image_id)
        cv.widget.image_id = image_id

        return cv
    else:
        kwargs["pinning"] = False

        out = Sidecar(title=title, anchor=anchor)
        with out:
            cv = CadViewer(
                height=height,
                cad_width=cad_width,
                tree_width=tree_width,
                title=out.title,
                anchor=anchor,
                **kwargs
            )
            display(cv.widget)

        out.resizeSidebar(cad_width + tree_width + 12)

        SIDECARS[title] = cv

        print(f'Done, see viewer "{title}". To access the viewer, use get_sidecar("{title}")')
        return cv


# def show(shapes, states, title=None, anchor=None, **kwargs):
#     if title is None:
#         viewer = open_viewer(title=None, anchor=None, **kwargs)
#     else:
#         viewer = get_sidecar(title)
#         if viewer is None:
#             raise RuntimeError(f"There is no viewer named {title}")

#     viewer.add_shapes(shapes, states, **kwargs)


def get_sidecar(title=None):
    if title is None:
        if DEFAULT is None:
            print("No default viewer found")
            return
        else:
            title = DEFAULT

    sidecar = SIDECARS.get(title)
    if sidecar is None:
        print(f'There is no viewer "{title}"')
        return

    if sidecar.disposed:
        del SIDECARS[title]
        print(f'There is no viewer "{title}"')
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


def set_sidecar(title, anchor="right"):
    global DEFAULT  # pylint: disable=global-statement

    DEFAULT = title
    if get_sidecar(title) is None:
        open_viewer(title, anchor=anchor)


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
