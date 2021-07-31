import json
import ipywidgets as widgets
from pyparsing import Literal, Word, alphanums, nums, delimitedList, ZeroOrMore
from traitlets import Unicode, Dict, List, Tuple, Integer, Float, Any, Bool
from .serializer import default
from IPython.display import display


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

    # Display traits

    cadWidth = Integer(default_value=800).tag(sync=True)
    height = Integer(default_value=600).tag(sync=True)
    treeWidth = Integer(default_vlue=240).tag(sync=True)
    theme = Unicode(default_value="light").tag(sync=True)
    tools = Bool(allow_none=True, default_value=True).tag(sync=True)

    # Viewer traits

    shapes = Unicode(allow_none=True).tag(sync=True)
    states = Dict(Tuple(Integer(), Integer()), allow_none=True).tag(sync=True)

    timeit = Bool(default_value=False, allow_None=True).tag(sync=True)
    needsAnimationLoop = Bool(default_value=False, allow_None=True).tag(sync=True)

    tracks = List(List(Float()), default_value=[], allow_none=True).tag(sync=True)

    position = Tuple(Float(), Float(), Float(), default_value=None, allow_none=True).tag(sync=True)
    zoom = Float(allow_none=True, default_value=None).tag(sync=True)

    ortho = Bool(allow_none=True, default_value=False).tag(sync=True)
    axes = Bool(allow_none=True, default_value=False).tag(sync=True)
    grid = Tuple(Bool(), Bool(), Bool(), default_value=[False, False, False], allow_none=True).tag(sync=True)
    ticks = Integer(default_value=10, allow_none=True).tag(sync=True)
    axes0 = Bool(allow_none=True, default_value=False).tag(sync=True)
    transparent = Bool(allow_none=True, default_value=False).tag(sync=True)
    black_edges = Bool(allow_none=True, default_value=False).tag(sync=True)

    bb_factor = Float(allow_none=True, default_value=1.0).tag(sync=True)
    default_edgecolor = Unicode(allow_none=True, default_value="#707070").tag(sync=True)
    ambient_intensity = Float(allow_none=True, default_value=0.9).tag(sync=True)
    direct_intensity = Float(allow_none=True, default_value=0.12).tag(sync=True)

    zoom_speed = Float(allow_none=True, default_value=0.5).tag(sync=True)
    pan_speed = Float(allow_none=True, default_value=0.5).tag(sync=True)
    rotate_speed = Float(allow_none=True, default_value=1.0).tag(sync=True)

    # UI traits

    clip_intersection = Bool(allow_none=True, default_value=False).tag(sync=True)
    clip_planes = Bool(allow_none=True, default_value=False).tag(sync=True)
    clip_normal_0 = Tuple(Float(), Float(), Float(), allow_none=True, default_value=[0.0, 0.0, 0.0]).tag(sync=True)
    clip_normal_1 = Tuple(Float(), Float(), Float(), allow_none=True, default_value=[0.0, 0.0, 0.0]).tag(sync=True)
    clip_normal_2 = Tuple(Float(), Float(), Float(), allow_none=True, default_value=[0.0, 0.0, 0.0]).tag(sync=True)
    clip_slider_0 = Float(allow_none=True, default_value=0.0).tag(sync=True)
    clip_slider_1 = Float(allow_none=True, default_value=0.0).tag(sync=True)
    clip_slider_2 = Float(allow_none=True, default_value=0.0).tag(sync=True)

    tab = Unicode(allow_none=True, default_value="tree").tag(sync=True)

    lastPick = Dict(Any(), allow_none=True, default_value={}).tag(sync=True)

    result = Unicode(allow_none=True, default_value="").tag(sync=True)


class CadViewer:
    def __init__(
        self,
        cadWidth=800,
        height=600,
        treeWidth=240,
        theme="light",
        tools=True,
    ):
        self.widget = CadViewerWidget(
            cadWidth=cadWidth,
            height=height,
            treeWidth=treeWidth,
            theme=theme,
            tools=tools,
        )
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

    def add_shapes(
        self,
        shapes,
        states,
        timeit=False,
        needsAnimationLoop=False,
        ortho=True,
        axes=False,
        grid=[False, False, False],
        axes0=False,
        ticks=10,
        transparent=False,
        black_edges=False,
        bb_factor=1.0,
        default_edgecolor="#707070",
        ambient_intensity=0.9,
        direct_intensity=0.12,
        tools=True,
    ):
        self.bb_factor = bb_factor
        self.default_edgecolor = default_edgecolor
        self.ambient_intensity = ambient_intensity
        self.direct_intensity = direct_intensity
        self.widget.axes = axes
        self.widget.axes0 = axes0
        self.widget.grid = grid
        self.widget.ticks = ticks
        self.widget.ortho = ortho
        self.widget.transparent = transparent
        self.widget.black_edges = black_edges
        self.widget.tools = tools
        self.widget.timeit = timeit
        self.widget.needsAnimationLoop = needsAnimationLoop
        self.widget.states = states
        self.widget.zoom = 1.0  # keep, else setting zoom later to 1 might fail

        # send shapes as the last traitlet to trigger rendering
        self.widget.shapes = json.dumps(shapes, default=default)

    def add_tracks(self, tracks):
        self.widget.tracks = tracks

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
