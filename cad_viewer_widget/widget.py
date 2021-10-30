"""This module is the Python part of the CAD Viewer widget"""

import json
import ipywidgets as widgets

from traitlets import Unicode, Dict, Tuple, Integer, Float, Any, Bool
from IPython.display import display
from pyparsing import ParseException

from .utils import serializer, check, check_list, get_parser


class AnimationTrack:
    """A three.js animation track"""

    def __init__(self, path, action, times, values):
        if len(times) != len(values):
            raise ValueError("Parameters 'times' and 'values' need to have same length")
        self.path = path
        self.action = action
        self.times = times
        self.values = values
        self.length = len(times)

    def to_array(self):
        """return track as 4 dim array"""
        return [self.path, self.action, self.times, self.values]


@widgets.register
class CadViewerWidget(widgets.Widget):  # pylint: disable-msg=too-many-instance-attributes
    """The CAD Viewer widget."""

    _view_name = Unicode("CadViewerView").tag(sync=True)
    _model_name = Unicode("CadViewerModel").tag(sync=True)
    _view_module = Unicode("cad-viewer-widget").tag(sync=True)
    _model_module = Unicode("cad-viewer-widget").tag(sync=True)
    _view_module_version = Unicode("^0.9.0").tag(sync=True)
    _model_module_version = Unicode("^0.9.0").tag(sync=True)

    #
    # Display traits
    #

    cad_width = Integer(default_value=800).tag(sync=True)
    height = Integer(default_value=600).tag(sync=True)
    tree_width = Integer(default_vlue=240).tag(sync=True)
    theme = Unicode(default_value="light").tag(sync=True)

    #
    # Viewer traits
    #

    shapes = Unicode(allow_none=True).tag(sync=True)
    states = Dict(Tuple(Integer(), Integer()), allow_none=True).tag(sync=True)

    tracks = Unicode(allow_none=True).tag(sync=True)

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

    #
    # Generic UI traits
    #

    tab = Unicode(allow_none=True, default_value="tree").tag(sync=True)
    clip_intersection = Bool(allow_none=True, default_value=False).tag(sync=True)
    clip_planes = Bool(allow_none=True, default_value=False).tag(sync=True)
    clip_normal_0 = Tuple(Float(), Float(), Float(), allow_none=True, default_value=[-1.0, 0.0, 0.0]).tag(sync=True)
    clip_normal_1 = Tuple(Float(), Float(), Float(), allow_none=True, default_value=[0.0, -1.0, 0.0]).tag(sync=True)
    clip_normal_2 = Tuple(Float(), Float(), Float(), allow_none=True, default_value=[0.0, 0.0, -1.0]).tag(sync=True)
    clip_slider_0 = Float(allow_none=True, default_value=0.0).tag(sync=True)
    clip_slider_1 = Float(allow_none=True, default_value=0.0).tag(sync=True)
    clip_slider_2 = Float(allow_none=True, default_value=0.0).tag(sync=True)

    position = Tuple(Float(), Float(), Float(), default_value=None, allow_none=True).tag(sync=True)
    quaternion = Tuple(Float(), Float(), Float(), Float(), default_value=None, allow_none=True).tag(sync=True)
    zoom = Float(allow_none=True, default_value=None).tag(sync=True)

    zoom_speed = Float(allow_none=True, default_value=0.5).tag(sync=True)
    pan_speed = Float(allow_none=True, default_value=0.5).tag(sync=True)
    rotate_speed = Float(allow_none=True, default_value=1.0).tag(sync=True)

    state_updates = Dict(Tuple(Integer(), Integer()), allow_none=True).tag(sync=True)

    #
    # Read only traitlets
    #

    lastPick = Dict(Any(), allow_none=True, default_value={}, read_only=True).tag(sync=True)
    target = Tuple(Float(), Float(), Float(), allow_none=True, read_only=True).tag(sync=True)

    initialize = Bool(allow_none=True, default_value=False).tag(sync=True)
    js_debug = Bool(allow_none=True, default_value=False).tag(sync=True)


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

        self.tracks = []

        display(self.widget)

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
        position=None,
        quaternion=None,
        zoom=None,
        reset_camera=True,
        timeit=False,
        # bb_factor=1.0,
    ):
        """Adding shapes to the CAD view"""

        if grid is None:
            grid = [False, False, False]

        self.widget.initialize = True

        # If one changes the control type, override reset_camera with "True"
        if self.widget.control != control:
            reset_camera = True
            print("Camera control changed, so camera was resetted")

        if control == "orbit" and quaternion is not None:
            quaternion = None
            print("Camera quaternion cannot be used with Orbit camera control")

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
            # reset camera if requested
            if reset_camera:
                self.widget.position = position
                self.widget.quaternion = quaternion
                self.widget.zoom = zoom
            else:
                if position is not None:
                    print("Parameter 'position' needs 'reset_camera=True'")
                if quaternion is not None:
                    print("Parameter 'quaternion' needs 'reset_camera=True'")
                if zoom is not None:
                    print("Parameter 'zoom' needs 'reset_camera=True'")

            # self.widget.bb_factor = bb_factor

        self.widget.initialize = False

    def update_states(self, states):
        """Set navigation tree states for a CAD view"""

        self.widget.state_updates = states

    #
    # UI and scene accessors
    #

    @property
    def ambient_intensity(self):
        """Get value of viewer attribute ambient_intensity"""

        return self.widget.ambient_intensity

    @ambient_intensity.setter
    def ambient_intensity(self, value):
        self.widget.ambient_intensity = check("ambient_intensity", value, (int, float))

    @property
    def direct_intensity(self):
        """Get value of viewer attribute direct_intensity"""

        return self.widget.direct_intensity

    @direct_intensity.setter
    def direct_intensity(self, value):
        self.widget.direct_intensity = check("direct_intensity", value, (int, float))

    @property
    def axes(self):
        """Get value of viewer attribute axes"""

        return self.widget.axes

    @axes.setter
    def axes(self, value):
        self.widget.axes = check("axes", value, bool)

    @property
    def axes0(self):
        """Get value of viewer attribute axes0"""

        return self.widget.axes0

    @axes0.setter
    def axes0(self, value):
        self.widget.axes0 = check("axes0", value, bool)

    @property
    def grid(self):
        """Get value of viewer attribute grid"""

        return self.widget.grid

    @grid.setter
    def grid(self, value):
        self.widget.grid = check_list("grid", value, bool, 3)

    @property
    def ortho(self):
        """Get value of viewer attribute ortho"""

        return self.widget.ortho

    @ortho.setter
    def ortho(self, value):
        self.widget.ortho = check("ortho", value, bool)

    @property
    def transparent(self):
        """Get value of viewer attribute transparent"""

        return self.widget.transparent

    @transparent.setter
    def transparent(self, value):
        self.widget.transparent = check("transparent", value, bool)

    @property
    def black_edges(self):
        """Get value of viewer attribute black_edges"""

        return self.widget.black_edges

    @black_edges.setter
    def black_edges(self, value):
        self.widget.black_edges = check("black_edges", value, bool)

    @property
    def edge_color(self):
        """Get value of viewer attribute edge_color"""

        return self.widget.edge_color

    @edge_color.setter
    def edge_color(self, value):
        check("edge_color", value, str)
        if value.startswith("#"):
            self.widget.edge_color = value
        else:
            self.widget.edge_color = f"#{value}"

    @property
    def clip_intersection(self):
        """Get value of viewer attribute clip_intersection"""

        return self.widget.clip_intersection

    @clip_intersection.setter
    def clip_intersection(self, value):
        self.widget.clip_intersection = check("clip_intersection", value, bool)

    @property
    def clip_normal_0(self):
        """Get value of viewer attribute clip_normal_0"""

        return self.widget.clip_normal_0

    @clip_normal_0.setter
    def clip_normal_0(self, value):
        self.widget.clip_normal_0 = check_list("clip_normal_0", value, (int, float), 3)

    @property
    def clip_normal_1(self):
        """Get value of viewer attribute clip_normal_1"""

        return self.widget.clip_normal_1

    @clip_normal_1.setter
    def clip_normal_1(self, value):
        self.widget.clip_normal_1 = check_list("clip_normal_1", value, (int, float), 3)

    @property
    def clip_normal_2(self):
        """Get value of viewer attribute clip_normal_2"""

        return self.widget.clip_normal_2

    @clip_normal_2.setter
    def clip_normal_2(self, value):
        self.widget.clip_normal_2 = check_list("clip_normal_2", value, (int, float), 3)

    @property
    def clip_value_0(self):
        """Get value of viewer attribute clip_slider_0"""

        return self.widget.clip_slider_0

    @clip_value_0.setter
    def clip_value_0(self, value):
        self.widget.clip_slider_0 = check("clip_value_0", value, (int, float))

    @property
    def clip_value_1(self):
        """Get value of viewer attribute clip_slider_1"""

        return self.widget.clip_slider_1

    @clip_value_1.setter
    def clip_value_1(self, value):
        self.widget.clip_slider_1 = check("clip_value_1", value, (int, float))

    @property
    def clip_value_2(self):
        """Get value of viewer attribute clip_slider_2"""

        return self.widget.clip_slider_2

    @clip_value_2.setter
    def clip_value_2(self, value):
        self.widget.clip_slider_2 = check("clip_value_2", value, (int, float))

    @property
    def clip_planes(self):
        """Get value of viewer attribute clip_planes"""

        return self.widget.clip_planes

    @clip_planes.setter
    def clip_planes(self, value):
        self.widget.clip_planes = check("clip_planes", value, bool)

    @property
    def js_debug(self):
        """Get value of viewer attribute js_debug"""

        return self.widget.js_debug

    @js_debug.setter
    def js_debug(self, value):
        self.widget.js_debug = check("js_debug", value, bool)

    @property
    def tools(self):
        """Get value of viewer attribute tools"""

        return self.widget.tools

    @tools.setter
    def tools(self, value):
        self.widget.tools = check("tools", value, bool)

    @property
    def pan_speed(self):
        """Get value of viewer attribute pan_speed"""

        return self.widget.pan_speed

    @pan_speed.setter
    def pan_speed(self, value):
        self.widget.pan_speed = check("pan_speed", value, (int, float))

    @property
    def rotate_speed(self):
        """Get value of viewer attribute rotate_speed"""

        return self.widget.rotate_speed

    @rotate_speed.setter
    def rotate_speed(self, value):
        self.widget.rotate_speed = check("rotate_speed", value, (int, float))

    @property
    def zoom_speed(self):
        """Get value of viewer attribute zoom_speed"""

        return self.widget.zoom_speed

    @zoom_speed.setter
    def zoom_speed(self, value):
        self.widget.zoom_speed = check("zoom_speed", value, (int, float))

    #
    # Camera position handling
    #

    @property
    def zoom(self):
        """Get value of viewer attribute zoom"""

        return self.widget.zoom

    @zoom.setter
    def zoom(self, value):
        self.widget.zoom = check("zoom", value, (int, float))

    @property
    def position(self):
        """Get value of viewer attribute position"""

        return self.widget.position

    @position.setter
    def position(self, value):
        self.widget.position = check_list("position", value, (int, float), 3)

    @property
    def quaternion(self):
        """Get value of viewer attribute quaternion"""

        return self.widget.quaternion

    @quaternion.setter
    def quaternion(self, value):
        self.widget.quaternion = check_list("quaternion", value, (int, float), 4)

    @property
    def last_pick(self):
        """Get value of viewer attribute lastPick"""

        return self.widget.lastPick

    @property
    def control(self):
        """Get value of viewer attribute control"""

        return self.widget.control

    #
    # Animation handling
    #

    def clear_tracks(self):
        """Remove animation tracks from CAD view"""

        self.tracks = []
        self.widget.tracks = ""

    def add_track(self, track):
        """Add an animation track to CAD view"""

        self.tracks.append(track)

    def add_tracks(self, tracks):
        """Add animation tracks to CAD view"""

        self.tracks = [] if tracks is None else [track for track in tracks]  # enforce a new array

    def animate(self, speed=1):
        """Send animation tracks to CAD view"""

        self.widget.tracks = json.dumps([track.to_array() for track in self.tracks])
        self.execute("animate", (speed,))
        self.play()

    def play(self):
        """Start animation"""

        self.execute("viewer.controlAnimation", ["play"])

    def stop(self):
        """Stop animation"""

        self.execute("viewer.controlAnimation", ["stop"])

    def pause(self):
        """Pause animation"""

        self.execute("viewer.controlAnimation", ["pause"])

    #
    # Tab handling
    #

    def select_tree(self):
        """Select Navigation tree tab"""
        self.widget.tab = "tree"

    def select_clipping(self):
        """Select Clipping tab"""
        self.widget.tab = "clip"

    #
    # Rotations
    #

    def rotate_x(self, angle):
        """Rotate CAD obj around x-axis - trackball controls only"""

        if self.control != "trackball":
            raise NameError("rotateX only works for trackball control")
        self.execute("viewer.controls.rotateX", (angle,))

    def rotate_y(self, angle):
        """Rotate CAD obj around y-axis - trackball controls only"""

        if self.control != "trackball":
            raise NameError("rotateY only works for trackball control")
        self.execute("viewer.controls.rotateY", (angle,))

    def rotate_z(self, angle):
        """Rotate CAD obj around z-axis - trackball controls only"""

        if self.control != "trackball":
            raise NameError("rotateZ only works for trackball control")
        self.execute("viewer.controls.rotateZ", (angle,))

    def rotate_up(self, angle):
        """Rotate CAD obj up (positive angle) and down (negative angle) - orbit controls only"""
        if self.control != "orbit":
            raise NameError("rotateUp only works for orbit control")
        self.execute("viewer.controls.rotateUp", (angle,))

    def rotate_left(self, angle):
        """Rotate CAD obj to the left (positive angle) and right (negative angle) - orbit controls only"""
        if self.control != "orbit":
            raise NameError("rotateLeft only works for orbit control")
        self.execute("viewer.controls.rotateLeft", (angle,))

    #
    # Custom message handling
    #

    def execute(self, method, args):
        """Execute a method of a Javascript object"""

        def wrapper(change=None):
            if change is None:
                self.msg_id += 1

                path = self._parse(method)

                content = {
                    "type": "cad_viewer_method",
                    "id": self.msg_id,
                    "method": json.dumps(path),
                    "args": json.dumps(args),
                }

                self.widget.send(content=content, buffers=None)

                return self.msg_id

        if args is not None and not isinstance(args, (tuple, list)):
            args = [args]
        return wrapper()

    def _ipython_display_(self):
        display(self.widget)
