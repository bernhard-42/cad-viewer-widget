from IPython.display import display
from sidecar import Sidecar

SIDECARS = {}
DEFAULT = None


def sidecar(name, clean=False, new=False, anchor="right"):
    sc = SIDECARS.get(name)

    if sc is not None:
        if clean:
            sc.outputs = ()
        elif new:
            sc.close()
            sc = None

    if sc is None:
        sc = Sidecar(title=name, anchor=anchor)
        SIDECARS[name] = sc

    return sc


def close_sidecar(title):
    if SIDECARS.get(title) is not None:
        SIDECARS[title].close()
        del SIDECARS[title]


def close_sidecars():
    global SIDECARS

    Sidecar.close_all()
    SIDECARS = {}


def get_sidecar(title=None):
    if title is None:
        return DEFAULT
    else:
        return SIDECARS.get(title)


def set_sidecar(name):
    global DEFAULT

    DEFAULT = name
    sidecar(name, clean=True)


def show(val, /, anchor="right", sidecar_name=None, clean=False, new=False):
    def _display(obj):
        if isinstance(obj, (int, float, str, bool)):
            print(obj)
        else:
            display(obj)

    if sidecar_name is None and DEFAULT is not None:
        sidecar_name = DEFAULT

    if sidecar_name is None:
        _display(val)
    else:
        with sidecar(sidecar_name, clean=clean, new=new, anchor=anchor):
            _display(val)
