import json
import ipywidgets as widgets
from pyparsing import Literal, Word, alphanums, nums, delimitedList, ZeroOrMore, Group
from traitlets import Unicode, Dict, List, Tuple, Integer, Float, Any, Bool
from .serializer import default
from IPython.display import display

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


def get_parser():
    dot = Literal(".").suppress()
    lbrack = Literal("[").suppress()
    rbrack = Literal("]").suppress()
    integer = Word(nums)
    index = lbrack + delimitedList(integer) + rbrack
    object = Word(alphanums + "_$") + ZeroOrMore(index)
    return object + ZeroOrMore(dot + object)


@widgets.register
class CadViewerWidget(widgets.Widget):
    """An example widget."""

    _view_name = Unicode("CadViewerView").tag(sync=True)
    _model_name = Unicode("CadViewerModel").tag(sync=True)
    _view_module = Unicode("cad-viewer-widget").tag(sync=True)
    _model_module = Unicode("cad-viewer-widget").tag(sync=True)
    _view_module_version = Unicode("^0.1.0").tag(sync=True)
    _model_module_version = Unicode("^0.1.0").tag(sync=True)

    #
    # model traits
    #

    options = Dict(Any()).tag(sync=True)

    shapes = Dict(
        per_key_traits={
            "shapes": Unicode(),
            "states": Dict(Tuple(Integer(), Integer())),
            "options": Dict(Any()),
        }
    ).tag(sync=True)

    tracks = List(
        List(Float()),
        default_value=[],
        allow_none=True,
    ).tag(sync=True)

    camera_position = Tuple(
        Float(),
        Float(),
        Float(),
        default_value=[0.0, 0.0, 0.0],
        allow_none=True,
    ).tag(sync=True)

    camera_zoom = Float(
        allow_none=True,
        default_value=1.0,
    ).tag(sync=True)

    tab = Unicode(
        allow_none=True,
        default_value="tree",
    ).tag(sync=True)

    ortho = Bool(
        allow_none=True,
        default_value=False,
    ).tag(sync=True)

    axes = Bool(
        allow_none=True,
        default_value=False,
    ).tag(sync=True)

    grid = Tuple(
        Bool(),
        Bool(),
        Bool(),
        default_value=[False, False, False],
        allow_none=True,
    ).tag(sync=True)

    axes0 = Bool(
        allow_none=True,
        default_value=False,
    ).tag(sync=True)

    transparent = Bool(
        allow_none=True,
        default_value=False,
    ).tag(sync=True)

    black_edges = Bool(
        allow_none=True,
        default_value=False,
    ).tag(sync=True)

    clip_intersection = Bool(
        allow_none=True,
        default_value=False,
    ).tag(sync=True)

    clip_planes = Bool(
        allow_none=True,
        default_value=False,
    ).tag(sync=True)

    clip_normal_0 = Tuple(
        Float(),
        Float(),
        Float(),
        allow_none=True,
        default_value=[0.0, 0.0, 0.0],
    ).tag(sync=True)

    clip_normal_1 = Tuple(
        Float(),
        Float(),
        Float(),
        allow_none=True,
        default_value=[0.0, 0.0, 0.0],
    ).tag(sync=True)

    clip_normal_2 = Tuple(
        Float(),
        Float(),
        Float(),
        allow_none=True,
        default_value=[0.0, 0.0, 0.0],
    ).tag(sync=True)

    clip_slider_0 = Float(
        allow_none=True,
        default_value=0.0,
    ).tag(sync=True)

    clip_slider_1 = Float(
        allow_none=True,
        default_value=0.0,
    ).tag(sync=True)

    clip_slider_2 = Float(
        allow_none=True,
        default_value=0.0,
    ).tag(sync=True)

    states = Dict(
        Any(),
        allow_none=True,
        default_value={},
    ).tag(sync=True)

    lastPick = Dict(
        Any(),
        allow_none=True,
        default_value={},
    ).tag(sync=True)

    result = Unicode(
        allow_none=True,
        default_value="",
    ).tag(sync=True)

    #
    # methods
    #

    def __init__(self, options=None, **kwargs):
        super().__init__(**kwargs)
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


class CadViewer:
    def __init__(self, options):
        self.widget = CadViewerWidget(options=options)
        self.msg_id = 0
        self.parser = get_parser()
        display(self.widget)

    #    self.widget.on_msg(self._on_message)

    # def _on_message(self, widget, content, buffers):
    #     if content["type"] == "cad_viewer_method_result":
    #         self.results[content["id"]] = json.loads(content["result"])

    def _parse(self, string):
        try:
            return self.parser.parseString(string).asList()
        except:
            return None

    def add_shapes(self, shapes, states, options=None):
        self.widget.add_shapes(shapes, states, options=options)

    def add_tracks(self, tracks):
        self.widget.add_tracks(tracks)

    def execute(self, object, method, args, threeType=None, update=False, callback=None):
        def wrapper(change=None):
            if change is None:
                self.widget.observe(wrapper, "result")
                self.msg_id += 1

                path = self._parse(object)

                content = {
                    "type": "cad_viewer_method",
                    "id": self.msg_id,
                    "object": json.dumps(path),
                    "name": method,
                    "args": json.dumps(args),
                    "threeType": threeType,
                    "update": update,
                }

                self.widget.send(content=content, buffers=None)

                return self.msg_id
            else:
                self.widget.unobserve(wrapper, "result")
                if callback is not None:
                    callback(change.new)

        if not isinstance(args, (tuple, list)):
            args = [args]
        return wrapper()

    def set(self, object, args, threeType=None, update=False, callback=None):
        return self.execute(object, "=", args, threeType, update, callback)

    def get(self, object, callback=None):
        return self.execute(object, None, None, None, None, callback)

    def get_result(self):
        return json.loads(self.widget.result)

    def _ipython_display_(self):
        display(self.widget)


def show_msg():
    def inner_show(msg):
        with out:
            print(msg)

    out = widgets.Output()
    display(out)

    return inner_show
