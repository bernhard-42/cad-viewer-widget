from IPython.display import display
from .widget import CadViewer
import time

SIDECARS = {}
DEFAULT = None


def open_viewer(title, anchor="right", **kwargs):
    cv = CadViewer(sidecar=title, anchor=anchor, **kwargs)
    SIDECARS[title] = cv
    display(cv.widget)
    print(f'Done, see viewer {title}. To access the viewer, use get_viewer("{title}")')


def get_viewer(title=None):
    if title is None:
        if DEFAULT is None:
            print("No default viewer found")
            return
        else:
            title = DEFAULT

    viewer = SIDECARS.get(title)
    if viewer is None:
        print(f'There is no viewer "{title}"')
        return

    if viewer.disposed:
        del SIDECARS[title]
        print(f'There is no viewer "{title}"')
        return
    
    return viewer

def get_viewers():
    viewers = {}
    deletions = []
    for title, viewer in SIDECARS.items():
        if viewer.disposed:
            deletions.append(title)
        else:
            viewers[title] = viewer
    
    for title in deletions:
        del SIDECARS[title]

    return viewers


def get_default():
    return DEFAULT


def set_viewer(title, anchor="right"):
    global DEFAULT

    DEFAULT = title
    if get_viewer(title) is None:
        open_viewer(title, anchor=anchor)


def close_viewers():
    global SIDECARS
    global DEFAULT

    for title, viewer in get_viewers().items():
        viewer.close()
        print(f'Closed viewer "{title}"')

    SIDECARS = {}
    DEFAULT = None


def close_viewer(title):
    viewer = SIDECARS.get(title)
    if viewer is not None:
        viewer.close()
        print(f'Closed viewer "{title}"')
