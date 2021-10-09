"""This module is the Python part of the CAD Viewer widget"""

import json
import ipywidgets as widgets
import numpy as np

from pyparsing import Literal, Word, alphanums, nums, delimitedList, ZeroOrMore, ParseException
from traitlets import Unicode, Dict, List, Tuple, Integer, Float, Any, Bool
from IPython.display import display
from .utils import serializer, rotate_x, rotate_y, rotate_z


def get_parser():
    """A parser for nested json objects"""
    dot = Literal(".").suppress()
    lbrack = Literal("[").suppress()
    rbrack = Literal("]").suppress()
    integer = Word(nums)
    index = lbrack + delimitedList(integer) + rbrack
    obj = Word(alphanums + "_$") + ZeroOrMore(index)
    return obj + ZeroOrMore(dot + obj)


@widgets.register
class CadViewerWidget(widgets.Widget):  # pylint: disable-msg=too-many-instance-attributes
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

    cad_width = Integer(default_value=800).tag(sync=True)
    height = Integer(default_value=600).tag(sync=True)
    tree_width = Integer(default_vlue=240).tag(sync=True)
    theme = Unicode(default_value="light").tag(sync=True)

    # Viewer traits

    shapes = Unicode(allow_none=True).tag(sync=True)
    states = Dict(Tuple(Integer(), Integer()), allow_none=True).tag(sync=True)
    tracks = List(List(Float()), default_value=[], allow_none=True).tag(sync=True)
    needs_animation_loop = Bool(default_value=False, allow_None=True).tag(sync=True)
    timeit = Bool(default_value=False, allow_None=True).tag(sync=True)
    tools = Bool(allow_none=True, default_value=True).tag(sync=True)

    ortho = Bool(allow_none=True, default_value=False).tag(sync=True)
    control = Unicode(default_value="trackball").tag(sync=True)
    axes = Bool(allow_none=True, default_value=False).tag(sync=True)
    axes0 = Bool(allow_none=True, default_value=False).tag(sync=True)
    grid = Tuple(Bool(), Bool(), Bool(), default_value=[False, False, False], allow_none=True).tag(sync=True)
    ticks = Integer(default_value=10, allow_none=True).tag(sync=True)
    transparent = Bool(allow_none=True, default_value=False).tag(sync=True)
    black_edges = Bool(allow_none=True, default_value=False).tag(sync=True)

    edge_color = Unicode(allow_none=True, default_value="#707070").tag(sync=True)
    ambient_intensity = Float(allow_none=True, default_value=0.9).tag(sync=True)
    direct_intensity = Float(allow_none=True, default_value=0.12).tag(sync=True)

    # bb_factor = Float(allow_none=True, default_value=1.0).tag(sync=True)

    # Generic UI traits

    tab = Unicode(allow_none=True, default_value="tree").tag(sync=True)
    clip_intersection = Bool(allow_none=True, default_value=False).tag(sync=True)
    clip_planes = Bool(allow_none=True, default_value=False).tag(sync=True)
    clip_normal_0 = Tuple(Float(), Float(), Float(), allow_none=True, default_value=[0.0, 0.0, 0.0]).tag(sync=True)
    clip_normal_1 = Tuple(Float(), Float(), Float(), allow_none=True, default_value=[0.0, 0.0, 0.0]).tag(sync=True)
    clip_normal_2 = Tuple(Float(), Float(), Float(), allow_none=True, default_value=[0.0, 0.0, 0.0]).tag(sync=True)
    clip_slider_0 = Float(allow_none=True, default_value=0.0).tag(sync=True)
    clip_slider_1 = Float(allow_none=True, default_value=0.0).tag(sync=True)
    clip_slider_2 = Float(allow_none=True, default_value=0.0).tag(sync=True)

    position = Tuple(Float(), Float(), Float(), default_value=None, allow_none=True).tag(sync=True)
    zoom = Float(allow_none=True, default_value=None).tag(sync=True)

    zoom_speed = Float(allow_none=True, default_value=0.5).tag(sync=True)
    pan_speed = Float(allow_none=True, default_value=0.5).tag(sync=True)
    rotate_speed = Float(allow_none=True, default_value=1.0).tag(sync=True)

    # Read only traitlets

    lastPick = Dict(Any(), allow_none=True, default_value={}, read_only=True).tag(sync=True)
    target = Tuple(Float(), Float(), Float(), allow_none=True, read_only=True).tag(sync=True)

    initialize = Bool(allow_none=True, default_value=False).tag(sync=True)
    result = Unicode(allow_none=True, default_value="", read_only=True).tag(sync=True)


class CadViewer:
    """The main class for the CAD Viewer encapsulationg the three-cad-viewer Javascript module"""

    def __init__(
        self,
        cad_width=800,
        height=600,
        tree_width=240,
        theme="light",
        tools=True,
    ):
        if cad_width < 640:
            raise ValueError("Ensure cad_width >= 640")
        if tree_width < 240:
            raise ValueError("Ensure tree_width >= 240")

        self.widget = CadViewerWidget(
            cad_width=cad_width,
            height=height,
            tree_width=tree_width,
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
        except ParseException:
            return None

    def add_shapes(
        self,
        shapes,
        states,
        tracks=None,
        ortho=True,
        control="trackball",
        axes=False,
        axes0=False,
        grid=None,
        ticks=10,
        transparent=False,
        black_edges=False,
        edge_color="#707070",
        ambient_intensity=0.9,
        direct_intensity=0.12,
        timeit=False,
        # bb_factor=1.0,
    ):
        """Adding shapes to the CAD view"""

        if grid is None:
            grid = [False, False, False]

        self.widget.initialize = True

        with self.widget.hold_trait_notifications():
            self.widget.shapes = json.dumps(shapes, default=serializer)
            self.widget.states = states
            self.widget.edge_color = edge_color
            self.widget.ambient_intensity = ambient_intensity
            self.widget.direct_intensity = direct_intensity
            self.widget.axes = axes
            self.widget.axes0 = axes0
            self.widget.grid = grid
            self.widget.ticks = ticks
            self.widget.ortho = ortho
            self.widget.control = control
            self.widget.transparent = transparent
            self.widget.black_edges = black_edges
            self.widget.timeit = timeit
            self.add_tracks(tracks)
            self.widget.needs_animation_loop = tracks is not None
            # self.widget.bb_factor = bb_factor

            self.widget.zoom = 1.0  # keep, else setting zoom later to 1 might fail

        self.widget.initialize = False

    def add_tracks(self, tracks):
        """Add animation tracks to a CAD view"""

        self.widget.tracks = tracks

    def set_states(self, states):
        """Set navigation tree states for a CAD view"""

        new_states = self.widget.states.copy()
        new_states.update(states)
        self.widget.states = new_states

    def _rotate(self, direction, angle):
        rot = {"x": rotate_x, "y": rotate_y, "z": rotate_z}
        new_pos = (
            rot[direction](np.asarray(self.widget.position) - np.asarray(self.widget.target), angle)
            + np.asarray(self.widget.target)
        ).tolist()
        self.widget.position = new_pos

    def rotate_x(self, angle):
        """Rotate CAD object around x axis"""
        self._rotate("x", angle)

    def rotate_y(self, angle):
        """Rotate CAD object around y axis"""
        self._rotate("y", angle)

    def rotate_z(self, angle):
        """Rotate CAD object around z axis"""
        self._rotate("z", angle)

    # def execute(self, method, args, callback=None):
    #     def wrapper(change=None):
    #         if change is None:
    #             self.widget.observe(wrapper, "result")
    #             self.msg_id += 1

    #             path = self._parse(method)

    #             content = {
    #                 "type": "cad_viewer_method",
    #                 "id": self.msg_id,
    #                 "method": json.dumps(path),
    #                 "args": json.dumps(args),
    #             }

    #             self.widget.send(content=content, buffers=None)

    #             return self.msg_id
    #         else:
    #             self.widget.unobserve(wrapper, "result")
    #             if callback is not None:
    #                 callback(change.new)

    #     if args is not None and not isinstance(args, (tuple, list)):
    #         args = [args]
    #     return wrapper()

    # def set(self, obj, args, three_type=None, update=False, callback=None):
    #     return self.execute(obj, "=", args, three_type, update, callback)

    # def get(self, obj, callback=None):
    #     return self.execute(obj, None, None, None, None, callback)

    # def get_result(self):
    #     return json.loads(self.widget.result)

    def _ipython_display_(self):
        display(self.widget)


def show_msg():
    def inner_show(msg):
        with out:
            print(msg)

    out = widgets.Output()
    display(out)

    return inner_show
