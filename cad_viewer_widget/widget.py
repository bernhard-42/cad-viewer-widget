import json
import ipywidgets as widgets
from traitlets import Unicode, Dict, List, Tuple, Integer, Float, Any
from .serializer import default
from IPython.display import HTML, display

display_options = {
    "cadWidth": 800,
    "height": 600,
    "treeWidth": 240,
    "theme": "light",
}

view_options = {
    "needsAnimationLoop": False,
    "measure": False,
    "ortho": True,
    "normalLen": 0,
    "ambientIntensity": 0.9,
    "directIntensity": 0.12,
}


@widgets.register
class CadViewer(widgets.DOMWidget):
    """An example widget."""

    _view_name = Unicode("CadViewerView").tag(sync=True)
    _model_name = Unicode("CadViewerModel").tag(sync=True)
    _view_module = Unicode("cad-viewer-widget").tag(sync=True)
    _model_module = Unicode("cad-viewer-widget").tag(sync=True)
    _view_module_version = Unicode("^0.1.0").tag(sync=True)
    _model_module_version = Unicode("^0.1.0").tag(sync=True)

    options = Dict(Any()).tag(sync=True)
    shapes = Dict(Any()).tag(sync=True)
    # dict(shapes=Unicode(), states=Dict(Tuple(Integer(), Integer())), options=Dict(Any()))).tag(sync=True)
    tracks = List(List(Float())).tag(sync=True)

    def __init__(self, options=None, **kwargs):
        super().__init__(**kwargs)
        html = """<link rel="stylesheet" href="https://unpkg.com/three-cad-viewer@0.9.0-beta.11/dist/three-cad-viewer.css">"""
        display(HTML(html))
        self.options = self._complete_options(options)

    def _complete_options(self, options):
        all_options = {}

        # add existing options ...
        if self.options is not None:
            all_options.update(self.options)

        # ... overwrite with newer options ...
        if options is not None:
            all_options.update(options)

        # ... and update all missing defaults
        for opts in (display_options, view_options):
            for k, v in opts.items():
                if all_options.get(k) is None:
                    all_options[k] = v

        return all_options

    def add_shapes(self, shapes, states, options=None):
        self.shapes = {
            "options": self._complete_options(options),
            "shapes": json.dumps(shapes, default=default),
            "states": states,
        }

    def add_tracks(self, tracks):
        self.tracks = tracks
