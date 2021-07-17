import ipywidgets as widgets
from traitlets import Unicode, Dict, List, Integer, Any


@widgets.register
class CadViewer(widgets.DOMWidget):
    """An example widget."""

    _view_name = Unicode("CadViewerView").tag(sync=True)
    _model_name = Unicode("CadViewerModel").tag(sync=True)
    _view_module = Unicode("cad-viewer-widget").tag(sync=True)
    _model_module = Unicode("cad-viewer-widget").tag(sync=True)
    _view_module_version = Unicode("^0.1.0").tag(sync=True)
    _model_module_version = Unicode("^0.1.0").tag(sync=True)

    shapes = Unicode("").tag(sync=True)
    states = Dict(List(Integer())).tag(sync=True)
    options = Dict(Any()).tag(sync=True)
    tracks = List(Unicode()).tag(sync=True)

    def __init__(self, shapes, states, options=None, tracks=None, **kwargs):
        super().__init__(**kwargs)
        self.shapes = shapes
        self.states = states
        self.options = {} if options is None else options
        self.tracks = [] if tracks is None else tracks
