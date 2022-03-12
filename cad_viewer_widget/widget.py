"""This module is the Python part of the CAD Viewer widget"""

import base64
import json
from textwrap import dedent

import numpy as np

import ipywidgets as widgets
from ipywidgets.embed import embed_minimal_html, dependency_state

from traitlets import Unicode, Dict, List, Tuple, Integer, Float, Any, Bool, observe
from IPython.display import HTML, update_display
from pyparsing import ParseException

from .utils import get_parser, to_json
from .boundingbox import combined_bb, normalize


class AnimationTrack:
    """
    Defining a three.js animation track.

    Parameters
    ----------
    path : string
        The path (or id) of the cad object for which this track is meant.
        Usually of the form `/top-level/level2/...`
    action : {"t", "tx", "ty", "tz", "q", "rx", "ry", "rz"}
        The action type:

        - "tx", "ty", "tz" for translations along the x, y or z-axis
        - "t" to add a position vector (3-dim array) to the current position of the CAD object
        - "rx", "ry", "rz" for rotations around x, y or z-axis
        - "q" to apply a quaternion to the location of the CAD object
    times : list of float or int
        An array of floats describing the points in time where CAD object (with id `path`) should be at the location
        defined by `action` and `values`
    values : list of float or int
        An array of same length as `times` defining the locations where the CAD objects should be according to the
        `action` provided. Formats:

        - "tx", "ty", "tz": float distance to move
        - "t": 3-dim tuples or lists defining the positions to move to
        - "rx", "ry", "rz": float angle in degrees
        - "q" quaternions of the form (x,y,z,w) the represent the rotation to be applied

    Examples
    --------
    ```
    AnimationTrack(
        '/bottom/left_middle/lower',                                # path
        'rz',                                                       # action
        [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],              # times (seconds)
        [-15.0, -15.0, -15.0, 9.7, 20.0, 9.7, -15.0, -15.0, -15.0]  # angles
    )

    AnimationTrack(
        'base/link_4_6',                                            # path
        't',                                                        # action
        [0.0, 1.0, 2.0, 3.0, 4.0],                                  # times (seconds)
        [[0.0, 0.0, 0.0], [0.0, 1.9509, 3.9049],
         [0.0 , -3.2974, -16.7545], [0.0 , 0.05894 , -32.0217],
         [0.0 , -3.2212, -13.3424]]                                 # 3-dim positions
    )
    ```

    See also
    --------

    - [three.js NumberKeyframeTrack](https://threejs.org/docs/index.html?q=track#api/en/animation/tracks/NumberKeyframeTrack)
    - [three.js QuaternionKeyframeTrack](https://threejs.org/docs/index.html?q=track#api/en/animation/tracks/QuaternionKeyframeTrack)

    """

    def __init__(self, path, action, times, values):
        if len(times) != len(values):
            raise ValueError("Parameters 'times' and 'values' need to have same length")
        self.path = path
        self.action = action
        self.times = times
        self.values = values
        self.length = len(times)

    def to_array(self):
        """
        Create an array representation of the animation track

        Returns
        -------
        array-like
            The 4 dim array comprising of the instance variables `path`, `action`, `times` and `values`
        """

        def tolist(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (list, tuple)):
                return [tolist(subarray) for subarray in obj]
            else:
                return obj

        return [self.path, self.action, tolist(self.times), tolist(self.values)]


@widgets.register
class CadViewerWidget(widgets.Output):  # pylint: disable-msg=too-many-instance-attributes
    """The CAD Viewer widget."""

    _view_name = Unicode("CadViewerView").tag(sync=True)
    _model_name = Unicode("CadViewerModel").tag(sync=True)
    _view_module = Unicode("cad-viewer-widget").tag(sync=True)
    _model_module = Unicode("cad-viewer-widget").tag(sync=True)
    _view_module_version = Unicode("1.1.1").tag(sync=True)
    _model_module_version = Unicode("1.1.1").tag(sync=True)

    #
    # Display traits
    #

    title = Unicode(allow_none=True).tag(sync=True)
    "unicode string of the title of the sidecar to be used. None means CAD view will be opened in cell"

    anchor = Unicode(allow_none=True).tag(sync=True)
    "unicode string whether to add a view to the right sidebar ('right') or as a tab to the main window ('tab')"

    cad_width = Integer().tag(sync=True)
    "unicode string: Width of the canvas element"

    height = Integer(allow_none=True).tag(sync=True)
    "int: Height of the canvas element"

    tree_width = Integer(allow_none=True).tag(sync=True)
    "int: Width of the navigation tree element"

    theme = Unicode(allow_none=True).tag(sync=True)
    "unicode string: UI theme, can be 'dark' or 'light' (default)"

    pinning = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to show the pin a png button or not"

    #
    # Viewer traits
    #

    shapes = Dict(allow_none=True).tag(sync=True, to_json=to_json)
    "unicode: Serialized nested tessellated shapes"

    states = Dict(Tuple(Integer(), Integer()), allow_none=True).tag(sync=True)
    "dict: State of the nested cad objects, key = object path, value = 2-dim tuple of 0/1 (hidden/visible) for object and edges"

    tracks = List(allow_none=True).tag(sync=True)
    "unicode: Serialized list of animation track arrays, see [AnimationTrack.to_array](/widget.html#cad_viewer_widget.widget.AnimationTrack.to_array)"

    timeit = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to output timing info to the browser console (True) or not (False)"

    tools = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to show CAD tools (True) or not (False)"

    ortho = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to use orthographic view (True) or perspective view (False)"

    control = Unicode().tag(sync=True)
    "unicode: Whether to use trackball controls ('trackball') or orbit controls ('orbit')"

    axes = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to show coordinate axes (True) or not (False)"

    axes0 = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to center coordinate axes at the origin [0,0,0] (True) or at the CAD object center (False)"

    grid = Tuple(Bool(), Bool(), Bool(), allow_none=True).tag(sync=True)
    "tuple: Whether to show the grids for `xy`, `xz`, `yz`."

    ticks = Integer(allow_none=True).tag(sync=True)
    "integer: Hint for the number of ticks for the grids (will be adjusted for nice intervals)"

    transparent = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to show the CAD objects transparently (True) or not (False)"

    black_edges = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to shows the edges in black (True) or not(False)"

    normal_len = Float(allow_none=True).tag(sync=True)
    "float: If > 0, the vertex normals will be rendered with the length given be this parameter"

    default_edge_color = Unicode(allow_none=True).tag(sync=True)
    "unicode: The default edge color in web format, e.g. '#ffaa88'"

    default_opacity = Float(allow_none=True).tag(sync=True)
    "unicode: The default opacity for transparent objects"

    ambient_intensity = Float(allow_none=True).tag(sync=True)
    "float: The intensity of the ambient light"

    direct_intensity = Float(allow_none=True).tag(sync=True)
    "float: The intensity of the 8 direct lights"

    #
    # Generic UI traits
    #

    tab = Unicode(allow_none=True).tag(sync=True)
    "unicode: Whether to show the navigation tree ('tree') or the clipping UI ('clip')"

    clip_intersection = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to use intersection clipping (True) or not (False)"

    clip_planes = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to show colored clipping planes (True) or not (False)"

    clip_normal_0 = Tuple(Float(), Float(), Float(), allow_none=True, default_value=None).tag(sync=True)
    "tuple: Normal of clipping plane 1 as a 3-dim tuple of float (x,y,z)"

    clip_normal_1 = Tuple(Float(), Float(), Float(), allow_none=True, default_value=None).tag(sync=True)
    "tuple: Normal of clipping plane 2 as a 3-dim tuple of float (x,y,z)"

    clip_normal_2 = Tuple(Float(), Float(), Float(), allow_none=True, default_value=None).tag(sync=True)
    "tuple: Normal of clipping plane 3 as a 3-dim tuple of float (x,y,z)"

    clip_slider_0 = Float(allow_none=True, default_value=None).tag(sync=True)
    "float: Slider value of clipping plane 1"

    clip_slider_1 = Float(allow_none=True, default_value=None).tag(sync=True)
    "float: Slider value of clipping plane 2"

    clip_slider_2 = Float(allow_none=True, default_value=None).tag(sync=True)
    "float: Slider value of clipping plane 3"

    reset_camera = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to reset camera (True) or not (False)"

    position = Tuple(Float(), Float(), Float(), allow_none=True).tag(sync=True)
    "tuple: Position of the camera as a 3-dim tuple of float (x,y,z)"

    quaternion = Tuple(Float(), Float(), Float(), Float(), allow_none=True).tag(sync=True)
    "tuple: Rotation of the camera as 4-dim quaternion (x,y,z,w)"

    target = Tuple(Float(), Float(), Float(), allow_none=True).tag(sync=True)
    "tuple: Camera target to look at as 3-dim tuple (x,y,z)"

    zoom = Float(allow_none=True).tag(sync=True)
    "float: Zoom value of the camera"

    position0 = Tuple(Float(), Float(), Float(), allow_none=True).tag(sync=True)
    "tuple: Initial position of the camera as a 3-dim tuple of float (x,y,z)"

    quaternion0 = Tuple(Float(), Float(), Float(), Float(), allow_none=True).tag(sync=True)
    "tuple: Initial rotation of the camera as 4-dim quaternion (x,y,z,w)"

    zoom0 = Float(allow_none=True).tag(sync=True)
    "float: Initial zoom value of the camera"

    target0 = Tuple(Float(), Float(), Float(), allow_none=True).tag(sync=True)
    "tuple: Initial camera target to look at as 3-dim tuple (x,y,z)"

    zoom_speed = Float(allow_none=True).tag(sync=True)
    "float: Speed of zooming with the mouse"

    pan_speed = Float(allow_none=True).tag(sync=True)
    "float: Speed of panning with the mouse"

    rotate_speed = Float(allow_none=True).tag(sync=True)
    "float: Speed of rotation with the mouse"

    animation_speed = Float(allow_none=True).tag(sync=True)
    "float: Animation speed"

    state_updates = Dict(Tuple(Integer(), Integer()), allow_none=True).tag(sync=True)
    "dict: Dict with paths as key and a 2-dim tuple of 0/1 (hidden/visible) for object and edges"

    #
    # Read only traitlets
    #

    lastPick = Dict(key_trait=Unicode(), value_trait=Any(), allow_none=True, read_only=True).tag(sync=True)
    "dict: Describes the last picked element of the CAD view"

    result = Unicode(allow_none=True).tag(sync=True)
    "unicode string: JSON serialized result from Javascript"

    #
    # Internal traitlets
    #

    disposed = Bool(default=False, allow_none=True, default_value=None).tag(sync=True)
    "unicode string: Whether the Javascript viewer is disposed"

    initialize = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: internally used to control initialization of view. Do not use!"

    js_debug = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to show infos in the browser console (True) or not (False)"

    image_id = Unicode(allow_none=True).tag(sync=True)
    "unicode string: the id of the image tag to use for pin as png"

    @observe("result")
    def func(self, change):
        if change["new"] is not None:
            data = json.loads(change["new"])

            if data.get("display_id") is not None:
                html = f"""<img src="{data['src']}" width="{data['width']}px" height="{data['height']}px"/>"""
                update_display(HTML(html), display_id=data["display_id"])
            else:
                if self.test_func is not None and callable(self.test_func):
                    self.test_func(base64.b64decode(data["src"].split(",")[1]))  # pylint: disable=not-callable
                else:
                    with open(data["filename"], "wb") as fd:
                        fd.write(base64.b64decode(data["src"].split(",")[1]))

            self.result = None


class CadViewer:
    """
    The main class for the CAD Viewer encapsulating the three-cad-viewer Javascript module

    Parameters
    ----------
    cad_width : int, default: 800
        Width of the canvas element
    height : int, default: 600
        Height of the canvas element
    tree_width : int, default: 240
        Width of the navigation tree element
    theme : string, default: 'light'
        UI theme, can be 'dark' or 'light' (default)
    tools : bool, default: True
        Whether to show CAD tools (True) or not (False)
    pinning: bool, default: False
        Whether to allow replacing the CAD View by a canvas screenshot

    See also
    --------

    - [three-cad-viewer](https://github.com/bernhard-42/three-cad-viewer) ([Demo](https://bernhard-42.github.io/three-cad-viewer/example.html))
    - [threejs](https://threejs.org/docs/index.html#manual/en/introduction/Creating-a-scene)

    """

    def __init__(
        self,
        cad_width=800,
        height=600,
        tree_width=240,
        theme="light",
        pinning=False,
        title=None,
        anchor=None,
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
            pinning=pinning,
            title=title,
            anchor=anchor,
        )
        self.widget.test_func = None
        self.msg_id = 0
        self.parser = get_parser()

        self.empty = True

        self.tracks = []

    def _parse(self, string):
        try:
            return self.parser.parseString(string).asList()
        except ParseException:
            return None

    def dispose(self):
        """
        Dispose the CAD Viewer
        """

        self.execute("viewer.dispose")

    def add_shapes(
        self,
        shapes,
        states,
        tracks=None,
        # render options
        normal_len=0,
        default_edge_color="#707070",
        default_opacity=0.5,
        ambient_intensity=0.5,
        direct_intensity=0.3,
        # viewer options
        tools=True,
        control="trackball",
        ortho=True,
        axes=False,
        axes0=False,
        grid=None,
        ticks=10,
        transparent=False,
        black_edges=False,
        position=None,
        quaternion=None,
        target=None,
        zoom=1.0,
        reset_camera=True,
        zoom_speed=1.0,
        pan_speed=1.0,
        rotate_speed=1.0,
        timeit=False,
        js_debug=False,
    ):
        """
        Adding shapes to the CAD view

        Parameters
        ----------
        shapes : dict
            Nested tessellated shapes
        states : dict
            State of the nested cad objects, key = object path, value = 2-dim tuple of 0/1 (hidden/visible) for object and edges
        tracks : list or tuple, default None
            List of animation track arrays, see [AnimationTrack.to_array](/widget.html#cad_viewer_widget.widget.AnimationTrack.to_array)
        title: str, default: None
            Name of the title view to display the shapes.
        ortho : bool, default True
            Whether to use orthographic view (True) or perspective view (False)
        control : string, default 'trackball'
            Whether to use trackball controls ('trackball') or orbit controls ('orbit')
        axes : bool, default False
            Whether to show coordinate axes (True) or not (False)
        axes0 : bool, default False
            Whether to center coordinate axes at the origin [0,0,0] (True) or at the CAD object center (False)
        grid : 3-dim list of bool, default None
            Whether to show the grids for `xy`, `xz`, `yz` (`None` means `(False, False, False)`)
        ticks : int, default 10
            Hint for the number of ticks for the grids (will be adjusted for nice intervals)
        transparent : bool, default False
            Whether to show the CAD objects transparently (True) or not (False)
        black_edges : bool, default False
            Whether to shows the edges in black (True) or not(False)
        normal_Len : int, default 0
            If > 0, the vertex normals will be rendered with the length given be this parameter
        default_edge_color : string, default "#707070"
            The default edge color in web format, e.g. '#ffaa88'
        default_opacity : float, default 0.5
            The default opacity level for transparency between 0.0 an 1.0
        ambient_intensity : float, default 0.9
            The intensity of the ambient light
        direct_intensity : float, default 0.12
            The intensity of the 8 direct lights
        position : 3-dim list of float, default None
            Position of the camera as a 3-dim tuple of float (x,y,z)
        quaternion : 4-dim list of float, default None
            Rotation of the camera as 4-dim quaternion (x,y,z,w)
        target :  3-dim list of float, default None
            Camera target to look at, default is the center of the object's bounding box
        zoom : float, default None
            Zoom value of the camera
        reset_camera : bool, default True
            Keep the camera position and rotation when showing new shapes (True) or not (False)
        zoom_speed : float, default 1.0
            Speed of zooming with the mouse
        pan_speed : float, default 1.0
            Speed of panning with the mouse
        rotate_speed : float, default 1.0
            Speed of rotation with the mouse
        timeit : bool, default False
            Whether to output timing info to the browser console (True) or not (False)

        Examples
        --------

        A simple cube with edge len of 1 is tessellated like the `shape` element of the first (and only) element of
        the `parts` list:

        ```
        shapes = {
            "name": "Group",
            "id": "/Group",
            "loc": None,  # would be (<position>, <quaternion>), e.g. ([0,0,0), (0,0,0,1)])
            "parts": [{
                "name": "Part_0",
                "id": "/Group/Part_0",
                "type": "shapes",
                "shape": {"vertices": [
                    [-0.5, -0.5, -0.5], [-0.5, -0.5, 0.5], [-0.5, 0.5, -0.5], [-0.5, 0.5, 0.5],
                    [0.5, -0.5, -0.5], [0.5, -0.5, 0.5], [0.5, 0.5, -0.5], [0.5, 0.5, 0.5],
                    [-0.5, -0.5, -0.5], [0.5, -0.5, -0.5], [-0.5, -0.5, 0.5], [0.5, -0.5, 0.5],
                    [-0.5, 0.5, -0.5], [0.5, 0.5, -0.5], [-0.5, 0.5, 0.5], [0.5, 0.5, 0.5],
                    [-0.5, -0.5, -0.5], [-0.5, 0.5, -0.5], [0.5, -0.5, -0.5], [0.5, 0.5, -0.5],
                    [-0.5, -0.5, 0.5], [-0.5, 0.5, 0.5], [0.5, -0.5, 0.5], [0.5, 0.5, 0.5]],
                "triangles": [
                    1, 2, 0, 1, 3, 2, 5, 4, 6, 5, 6, 7, 11, 8, 9, 11, 10, 8, 15, 13,
                    12, 15, 12, 14, 19, 16, 17, 19, 18, 16, 23, 21, 20, 23, 20, 22 ],
                "normals": [
                    [-1, 0, 0], [-1, 0, 0], [-1, 0, 0], [-1, 0, 0],
                    [1, 0, 0], [1, 0, 0], [1, 0, 0], [1, 0, 0],
                    [0, -1, 0], [0, -1, 0], [0, -1, 0], [0, -1, 0],
                    [0, 1, 0], [0, 1, 0], [0, 1, 0], [0, 1, 0],
                    [0, 0, -1], [0, 0, -1], [0, 0, -1], [0, 0, -1],
                    [0, 0, 1], [0, 0, 1], [0, 0, 1], [0, 0, 1]
                ],
                "edges": [
                    [[-0.5, -0.5, -0.5], [-0.5, -0.5, 0.5]],
                    [[-0.5, -0.5, 0.5], [-0.5, 0.5, 0.5]],
                    [[-0.5, 0.5, -0.5], [-0.5, 0.5, 0.5]],
                    [[-0.5, -0.5, -0.5], [-0.5, 0.5, -0.5]],
                    [[0.5, -0.5, -0.5], [0.5, -0.5, 0.5]],
                    [[0.5, -0.5, 0.5], [0.5, 0.5, 0.5]],
                    [[0.5, 0.5, -0.5], [0.5, 0.5, 0.5]],
                    [[0.5, -0.5, -0.5], [0.5, 0.5, -0.5]],
                    [[-0.5, -0.5, -0.5], [0.5, -0.5, -0.5]],
                    [[-0.5, -0.5, 0.5], [0.5, -0.5, 0.5]],
                    [[-0.5, 0.5, -0.5], [0.5, 0.5, -0.5]],
                    [[-0.5, 0.5, 0.5], [0.5, 0.5, 0.5]]
                ]},
                "color": "#e8b024",
                "renderback": false,
                "bb": {
                    "xmin": -0.5, "xmax": 0.5,
                    "ymin": -0.5, "ymax": 0.5,
                    "zmin": -0.5, "zmax": 0.5
                }
            }]
        }
        states = {'/Group/Part_0': [1, 1]}
        ```

        A nested object (with shapes shortened) looks like:

        ```
        {
            'id': '/bottom', 'name': 'bottom', 'loc': ['<position>', '<quaternion>'],
            'parts': [{
                    'id': '/bottom/bottom_0', 'name': 'bottom_0', 'type': 'shapes', 'color': '#bfbfbf',
                    'shape': {'vertices': [...], 'triangles': [...], 'normals': [...], 'edges': [...]},
                }, {
                    'id': '/bottom/top', 'name': 'top', 'loc': ['<position>', '<quaternion>'],
                    'parts': [{
                        'id': '/bottom/top/top_0', 'name': 'top_0', 'type': 'shapes', 'color': '#bfbfbf',
                        'shape': {'vertices': [...], 'triangles': [...], 'normals': [...], 'edges': [...]},
                    }]
                }, {
                    'id': '/bottom/front_stand', 'name': 'front_stand', 'loc': ['<position>', '<quaternion>'],
                    'parts': [{
                        'id': '/bottom/front_stand/front_stand_0', 'name': 'front_stand_0', 'type': 'shapes', 'color': '#7fcce5',
                        'shape': {'vertices': [...], 'triangles': [...], 'normals': [...], 'edges': [...]},
                    }]
                }, {
                    'id': '/bottom/back_stand', 'name': 'back_stand', 'loc': ['<position>', '<quaternion>'],
                    'parts': [{
                        'id': '/bottom/back_stand/back_stand_0', 'name': 'back_stand_0', 'type': 'shapes', 'color': '#7fcce5',
                        'shape': {'vertices': [...], 'triangles': [...], 'normals': [...], 'edges': [...]},
                    }]
                }, {
                    'id': '/bottom/right_back', 'name': 'right_back', 'loc': ['<position>', '<quaternion>'],
                    'parts': [{
                        'id': '/bottom/right_back/right_back_0', 'name': 'right_back_0', 'type': 'shapes', 'color': '#ffa500',
                        'shape': {'vertices': [...], 'triangles': [...], 'normals': [...], 'edges': [...]},
                    }, {
                        'id': '/bottom/right_back/lower', 'name': 'lower', 'loc': ['<position>', '<quaternion>'],
                        'parts': [{
                            'id': '/bottom/right_back/lower/lower_0', 'name': 'lower_0', 'type': 'shapes', 'color': '#ffa500',
                            'shape': {'vertices': [...], 'triangles': [...], 'normals': [...], 'edges': [...]},
                        }]
                    }]
                },
                ...
            ]
        }
        states = {
            '/bottom/bottom_0': [1, 1],
            '/bottom/top/top_0': [1, 1],
            '/bottom/front_stand/front_stand_0': [1, 1],
            '/bottom/back_stand/back_stand_0': [1, 1],
            '/bottom/right_back/right_back_0': [1, 1],
            '/bottom/right_back/lower/lower_0': [1, 1],
            ...
        }
        ```

        Notes
        -----

        Vector     : float[3]     := [x, y, z]
        VectorList : Vector[n]    := [ [x0, y0, z0], [x1, xy1, z1], ... ]
        Index      : int[m]       := [ i0, i1, i2, ... ]
        Edge       : Vector[2]    := [ [x0, y0, z0], [x1, xy1, z1]]
        EdgeList   : Edge[k]      := [ [[x0, y0, z0], [x1, xy1, z1]], [[x2, y2, z2], [x3, xy3, z3]], ... ]

        Shape, Faces := {
            "id": "<str>",
            "name": "<str>",
            "type": "shapes",
            "color": "#ffffff",
            "renderback": false,
            "bb": {
                "xmin": -0.5, "xmax": 0.5,
                "ymin": -0.5, "ymax": 0.5,
                "zmin": -0.5, "zmax": 0.5
            },
            "shape": {
                "vertices": <VectorList>,
                "triangles": <Index>,
                "normals": <VectorList>,
                "edges": <EdgeList>
            }
        }

        Edges := {
            "id": "</path/to/<name>>",
            "name": "<name>",
            "type": "edges",
            "color": "#ffffff",
            "width": 3,
            "renderback": false,
            "bb": {
                "xmin": -0.5, "xmax": 0.5,
                "ymin": -0.5, "ymax": 0.5,
                "zmin": -0.5, "zmax": 0.5
            },
            "shape": <EdgeList>
        }

        Vertices := {
            "id": "</path/to/<name>>",
            "name": "<name>",
            "type": "vertices",
            "color": "#ffffff",
            "size": 6,
            "bb": {
                "xmin":  -5.0, "xmax": 5.0,
                "ymin": -10.0, "ymax": 10.0,
                "zmin": -15.0, "zmax": 15.0
            },
            "shape": <VectorList>
        }
        """

        if control == "orbit" and quaternion is not None:
            raise ValueError("Camera quaternion cannot be used with Orbit camera control")

        if control == "trackball" and position is not None and quaternion is None:
            raise ValueError("For Trackball camera control, position paramater also needs quaternion parameter")

        if grid is None:
            grid = [False, False, False]

        # If one changes the control type, override reset_camera with "True"
        if self.empty or self.widget.control != control:
            reset_camera = True
            self.empty = False

            # Don't show warning on first call
            if self.widget.control != "":
                print("Camera control changed, so camera was resetted")

        if reset_camera:
            bb = combined_bb(shapes)

            if position is None:
                position = (
                    normalize(np.array((1, 1, 1))) * 5.5 * bb.max_dist_from_center() + np.array(bb.center)
                ).tolist()

            if quaternion is None and control == "trackball":
                quaternion = (
                    0.1759198966061612,
                    0.42470820027786693,
                    0.8204732385702833,
                    0.33985114297998736,
                )

            if target is None:
                target = bb.center

            if zoom is None:
                zoom = 1.0
        else:
            copy = lambda v: None if v is None else (*v,)
            position = copy(self.widget.position)
            quaternion = copy(self.widget.quaternion)
            target = copy(self.widget.target)
            zoom = self.widget.zoom

        self.widget.initialize = True

        with self.widget.hold_trait_notifications():
            self.widget.shapes = shapes
            self.widget.states = states

            self.widget.default_edge_color = default_edge_color
            self.widget.default_opacity = default_opacity
            self.widget.ambient_intensity = ambient_intensity
            self.widget.direct_intensity = direct_intensity
            self.widget.normal_len = normal_len

            self.widget.tools = tools
            self.widget.control = control
            self.widget.axes = axes
            self.widget.axes0 = axes0
            self.widget.grid = grid
            self.widget.ticks = ticks
            self.widget.ortho = ortho
            self.widget.transparent = transparent
            self.widget.black_edges = black_edges
            self.widget.reset_camera = reset_camera
            self.widget.position = position
            self.widget.quaternion = quaternion
            self.widget.target = target
            self.widget.zoom = zoom
            # If reset_camera, position0, quaternion0 and zoom0 need to be set
            if reset_camera:
                self.widget.position0 = (*position,)
                if control == "trackball":
                    self.widget.quaternion0 = (*quaternion,)
                self.widget.target0 = (*target,)
                self.widget.zoom0 = zoom
            self.widget.zoom_speed = zoom_speed
            self.widget.pan_speed = pan_speed
            self.widget.rotate_speed = rotate_speed
            self.widget.timeit = timeit
            self.widget.js_debug = js_debug
            self.add_tracks(tracks)

        self.widget.initialize = False
        # self.update_camera_location()

    def update_states(self, states):
        """Set navigation tree states for a CAD view"""

        self.widget.state_updates = states

    def update_camera_location(self):
        """Sync position, quaternion and zoom of camera to Python"""
        self.execute("updateCamera", [])

    def close(self):
        """
        Close the underlying Javascript viewer
        """
        self.widget.disposed = True

    @property
    def disposed(self):
        """
        Whether the Javascript viewer is disposed
        """

        return self.widget.disposed

    #
    # UI and scene accessors
    #

    @property
    def ambient_intensity(self):
        """
        Get or set the CadViewerWidget traitlet `ambient_intensity`.
        see [CadViewerWidget.ambient_intensity](./widget.html#cad_viewer_widget.widget.CadViewerWidget.ambient_intensity)
        """

        return self.widget.ambient_intensity

    @ambient_intensity.setter
    def ambient_intensity(self, value):
        self.widget.ambient_intensity = value

    @property
    def direct_intensity(self):
        """
        Get or set the CadViewerWidget traitlet `direct_intensity`
        see [CadViewerWidget.direct_intensity](./widget.html#cad_viewer_widget.widget.CadViewerWidget.direct_intensity)
        """

        return self.widget.direct_intensity

    @direct_intensity.setter
    def direct_intensity(self, value):
        self.widget.direct_intensity = value

    @property
    def axes(self):
        """
        Get or set the CadViewerWidget traitlet `axes`
        see [CadViewerWidget.axes](./widget.html#cad_viewer_widget.widget.CadViewerWidget.axes)
        """

        return self.widget.axes

    @axes.setter
    def axes(self, value):
        self.widget.axes = value

    @property
    def axes0(self):
        """
        Get or set the CadViewerWidget traitlet `axes0`
        see [CadViewerWidget.axes0](./widget.html#cad_viewer_widget.widget.CadViewerWidget.axes0)
        """

        return self.widget.axes0

    @axes0.setter
    def axes0(self, value):
        self.widget.axes0 = value

    @property
    def grid(self):
        """
        Get or set the CadViewerWidget traitlet `grid`
        see [CadViewerWidget.grid](./widget.html#cad_viewer_widget.widget.CadViewerWidget.grid)
        """

        return self.widget.grid

    @grid.setter
    def grid(self, value):
        self.widget.grid = value

    @property
    def ortho(self):
        """
        Get or set the CadViewerWidget traitlet `ortho`
        see [CadViewerWidget.ortho](./widget.html#cad_viewer_widget.widget.CadViewerWidget.ortho)
        """

        return self.widget.ortho

    @ortho.setter
    def ortho(self, value):
        self.widget.ortho = value

    @property
    def transparent(self):
        """
        Get or set the CadViewerWidget traitlet `transparent`
        see [CadViewerWidget.transparent](./widget.html#cad_viewer_widget.widget.CadViewerWidget.transparent)
        """

        return self.widget.transparent

    @transparent.setter
    def transparent(self, value):
        self.widget.transparent = value

    @property
    def black_edges(self):
        """
        Get or set the CadViewerWidget traitlet `black_edges`
        see [CadViewerWidget.black_edges](./widget.html#cad_viewer_widget.widget.CadViewerWidget.black_edges)
        """

        return self.widget.black_edges

    @black_edges.setter
    def black_edges(self, value):
        self.widget.black_edges = value

    @property
    def normal_len(self):
        """
        Get or set the CadViewerWidget traitlet `normal_len`
        """

        return self.widget.black_edges

    @property
    def default_edge_color(self):
        """
        Get or set the CadViewerWidget traitlet `default_edge_color`
        see [CadViewerWidget.default_edge_color](./widget.html#cad_viewer_widget.widget.CadViewerWidget.default_edge_color)
        """

        return self.widget.default_edge_color

    @default_edge_color.setter
    def default_edge_color(self, value):
        if value.startswith("#"):
            self.widget.default_edge_color = value
        else:
            self.widget.default_edge_color = f"#{value}"

    @property
    def default_opacity(self):
        """
        Get or set the CadViewerWidget traitlet `default_opacity`
        see [CadViewerWidget.default_opacity](./widget.html#cad_viewer_widget.widget.CadViewerWidget.default_opacity)
        """

        return self.widget.default_opacity

    @default_opacity.setter
    def default_opacity(self, value):
        if value.startswith("#"):
            self.widget.default_opacity = value
        else:
            self.widget.default_opacity = f"#{value}"

    @property
    def clip_intersection(self):
        """
        Get or set the CadViewerWidget traitlet `clip_intersection`
        see [CadViewerWidget.clip_intersection](./widget.html#cad_viewer_widget.widget.CadViewerWidget.clip_intersection)
        """

        return self.widget.clip_intersection

    @clip_intersection.setter
    def clip_intersection(self, value):
        self.widget.clip_intersection = value

    @property
    def clip_normal_0(self):
        """
        Get or set the CadViewerWidget traitlet `clip_normal_0`
        see [CadViewerWidget.clip_normal_0](./widget.html#cad_viewer_widget.widget.CadViewerWidget.clip_normal_0)
        """

        return self.widget.clip_normal_0

    @clip_normal_0.setter
    def clip_normal_0(self, value):
        self.widget.clip_normal_0 = value

    @property
    def clip_normal_1(self):
        """
        Get or set the CadViewerWidget traitlet `clip_normal_1`
        see [CadViewerWidget.clip_normal_1](./widget.html#cad_viewer_widget.widget.CadViewerWidget.clip_normal_1)
        """

        return self.widget.clip_normal_1

    @clip_normal_1.setter
    def clip_normal_1(self, value):
        self.widget.clip_normal_1 = value

    @property
    def clip_normal_2(self):
        """
        Get or set the CadViewerWidget traitlet `clip_normal_2`
        see [CadViewerWidget.clip_normal_2](./widget.html#cad_viewer_widget.widget.CadViewerWidget.clip_normal_2)
        """

        return self.widget.clip_normal_2

    @clip_normal_2.setter
    def clip_normal_2(self, value):
        self.widget.clip_normal_2 = value

    @property
    def clip_value_0(self):
        """
        Get or set the CadViewerWidget traitlet `clip_slider_0`
        see [CadViewerWidget.clip_slider_0](./widget.html#cad_viewer_widget.widget.CadViewerWidget.clip_slider_0)
        """

        return self.widget.clip_slider_0

    @clip_value_0.setter
    def clip_value_0(self, value):
        self.widget.clip_slider_0 = value

    @property
    def clip_value_1(self):
        """
        Get or set the CadViewerWidget traitlet `clip_slider_1`
        see [CadViewerWidget.clip_slider_1](./widget.html#cad_viewer_widget.widget.CadViewerWidget.clip_slider_1)
        """

        return self.widget.clip_slider_1

    @clip_value_1.setter
    def clip_value_1(self, value):
        self.widget.clip_slider_1 = value

    @property
    def clip_value_2(self):
        """
        Get or set the CadViewerWidget traitlet `clip_slider_2`
        see [CadViewerWidget.clip_slider_2](./widget.html#cad_viewer_widget.widget.CadViewerWidget.clip_slider_2)
        """

        return self.widget.clip_slider_2

    @clip_value_2.setter
    def clip_value_2(self, value):
        self.widget.clip_slider_2 = value

    @property
    def clip_planes(self):
        """
        Get or set the CadViewerWidget traitlet `clip_planes`
        see [CadViewerWidget.clip_planes](./widget.html#cad_viewer_widget.widget.CadViewerWidget.clip_planes)
        """

        return self.widget.clip_planes

    @clip_planes.setter
    def clip_planes(self, value):
        self.widget.clip_planes = value

    @property
    def js_debug(self):
        """
        Get or set the CadViewerWidget traitlet `js_debug`
        see [CadViewerWidget.js_debug](./widget.html#cad_viewer_widget.widget.CadViewerWidget.js_debug)
        """

        return self.widget.js_debug

    @js_debug.setter
    def js_debug(self, value):
        self.widget.js_debug = value

    @property
    def tools(self):
        """
        Get or set the CadViewerWidget traitlet `tools`
        see [CadViewerWidget.tools](./widget.html#cad_viewer_widget.widget.CadViewerWidget.tools)
        """

        return self.widget.tools

    @tools.setter
    def tools(self, value):
        self.widget.tools = value

    @property
    def pan_speed(self):
        """
        Get or set the CadViewerWidget traitlet `pan_speed`
        see [CadViewerWidget.pan_speed](./widget.html#cad_viewer_widget.widget.CadViewerWidget.pan_speed)
        """

        return self.widget.pan_speed

    @pan_speed.setter
    def pan_speed(self, value):
        self.widget.pan_speed = value

    @property
    def rotate_speed(self):
        """
        Get or set the CadViewerWidget traitlet `rotate_speed`
        see [CadViewerWidget.rotate_speed](./widget.html#cad_viewer_widget.widget.CadViewerWidget.rotate_speed)
        """

        return self.widget.rotate_speed

    @rotate_speed.setter
    def rotate_speed(self, value):
        self.widget.rotate_speed = value

    @property
    def zoom_speed(self):
        """
        Get or set the CadViewerWidget traitlet `zoom_speed`
        see [CadViewerWidget.zoom_speed](./widget.html#cad_viewer_widget.widget.CadViewerWidget.zoom_speed)
        """

        return self.widget.zoom_speed

    @zoom_speed.setter
    def zoom_speed(self, value):
        self.widget.zoom_speed = value

    #
    # Camera position handling
    #

    @property
    def zoom(self):
        """
        Get or set the CadViewerWidget traitlet `zoom`
        see [CadViewerWidget.zoom](./widget.html#cad_viewer_widget.widget.CadViewerWidget.zoom)
        """

        return self.widget.zoom

    @zoom.setter
    def zoom(self, value):
        self.widget.zoom = value

    @property
    def position(self):
        """
        Get or set the CadViewerWidget traitlet `position`
        see [CadViewerWidget.position](./widget.html#cad_viewer_widget.widget.CadViewerWidget.position)
        """

        return self.widget.position

    @position.setter
    def position(self, value):
        self.widget.position = value

    @property
    def quaternion(self):
        """
        Get or set the CadViewerWidget traitlet `quaternion`
        see [CadViewerWidget.quaternion](./widget.html#cad_viewer_widget.widget.CadViewerWidget.quaternion)
        """

        if self.widget.control == "orbit":
            print("quaternion controlled internally for control=='orbit'")
            return None
        else:
            return self.widget.quaternion

    @quaternion.setter
    def quaternion(self, value):
        if self.widget.control == "orbit":
            print("quaternion controlled internally for control=='orbit'")
        else:
            self.widget.quaternion = value

    @property
    def target(self):
        """
        Get or set the CadViewerWidget traitlet `target`
        see [CadViewerWidget.position](./widget.html#cad_viewer_widget.widget.CadViewerWidget.target)
        """

        # self.update_camera_location()
        return self.widget.target

    @target.setter
    def target(self, value):
        self.widget.target = value

    @property
    def last_pick(self):
        """
        Get or set the CadViewerWidget traitlet `lastPick`
        see [CadViewerWidget.lastPick](./widget.html#cad_viewer_widget.widget.CadViewerWidget.lastPick)
        """

        return self.widget.lastPick

    @property
    def control(self):
        """
        Get or set the CadViewerWidget traitlet `control`
        see [CadViewerWidget.control](./widget.html#cad_viewer_widget.widget.CadViewerWidget.control)
        """

        return self.widget.control

    @property
    def pinning(self):
        """
        Get or set the CadViewerWidget traitlet `pinning`
        see [CadViewerWidget.pinning](./widget.html#cad_viewer_widget.widget.CadViewerWidget.pinning)
        """
        return self.widget.pinning

    @pinning.setter
    def pinning(self, flag):
        self.widget.pinning = flag

    #
    # Animation handling
    #

    def clear_tracks(self):
        """
        Remove animation tracks from CAD view
        """

        self.tracks = []
        self.widget.tracks = []

    def _check_track(self, track):
        paths = self.widget.states.keys()
        if not any([(f"{path}/").startswith(f"{track.path}/") for path in paths]):
            raise ValueError(f"{track.path} is not a valid subpath of any of {list(paths)}")

        actions = ["t", "tx", "ty", "tz", "q", "rx", "ry", "rz"]
        if not track.action in actions:
            raise ValueError(f"{track.action} is not a valid action {list(actions)}")

        if len(track.times) != len(track.values):
            raise ValueError(f"Track times and values need to have same length")

        if not all([isinstance(t, (int, float)) for t in track.times]):
            raise ValueError(f"Time values need to be int or float")

        if track.action in ["tx", "ty", "tz", "rx", "ry", "rz"]:
            if not all([isinstance(t, (int, float)) for t in track.values]):
                raise ValueError(f"Value values need to be int or float for action '{track.action}'")

        if track.action in ["t", "q"]:
            size = 3 if track.action == "t" else 4
            if not all(
                [
                    isinstance(v, (list, tuple)) and (len(v) == size) and all([isinstance(x, (int, float)) for x in v])
                    for v in track.values
                ]
            ):
                raise ValueError(
                    f"Value values need to be {size} dim lists of int or float for action '{track.action}'"
                )

        return track

    def add_track(self, track):
        """
        Add an animation track to CAD view

        Parameters
        ----------
        track: AnimationTrack
            Animation track, see [AnimationTrack](/widget.html#cad_viewer_widget.widget.AnimationTrack)
        """

        self.tracks.append(self._check_track(track))

    def add_tracks(self, tracks):
        """
        Add a list of animation tracks to CAD view

        Parameters
        ----------
        tracks: list of AnimationTrack
            List of Animation tracks, see [AnimationTrack](/widget.html#cad_viewer_widget.widget.AnimationTrack)
        """
        checked_tracks = (
            [] if tracks is None else [self._check_track(track) for track in tracks]
        )  # enforce a new array
        self.tracks = checked_tracks

    def animate(self, speed=1):
        """
        Send animation tracks to CAD view

        Parameters
        ----------
        speed : float, default: 1
            Animation speed, will be forwarded via `animation_speed` traitlet
        """

        self.widget.tracks = [track.to_array() for track in self.tracks]
        self.widget.animation_speed = speed
        self.execute("animate")
        # self.play()

    def play(self):
        """
        Start or unpause animation
        """

        self.execute("viewer.controlAnimation", ["play"])

    def stop(self):
        """
        Stop animation
        """

        self.execute("viewer.controlAnimation", ["stop"])

    def pause(self):
        """
        Pause or unpause animation
        """

        self.execute("viewer.controlAnimation", ["pause"])

    def pin_as_png(self):
        """
        Pin CAD View as PNG
        """

        self.execute("pinAsPng", None)

    def export_png(self, filename):
        """
        Save CAD View as PNG
        """

        self.execute("saveAsPng", filename)

    #
    # Tab handling
    #

    def select_tree(self):
        """
        Select Navigation tree tab
        """

        self.widget.tab = "tree"

    def select_clipping(self):
        """
        Select Clipping tab
        """

        self.widget.tab = "clip"

    #
    # Rotations
    #

    def set_camera(self, direction):
        """
        Set camera to one of the predefined locations

        Parameters
        ----------
        direction : string
            one of ["iso", "top", "bottom", "left", "right", "front", "rear"]
        """

        self.execute("viewer.camera.presetCamera", [direction])
        self.execute("viewer.update", [])

    def rotate_x(self, angle):
        """
        Rotate CAD obj around x-axis - trackball controls only

        Parameters
        ----------
        angle : float
            The rotation angle in degrees
        """

        if self.control != "trackball":
            raise NameError("rotateX only works for trackball control")
        self.execute("viewer.controls.rotateX", (angle,))

    def rotate_y(self, angle):
        """
        Rotate CAD obj around y-axis - trackball controls only

        Parameters
        ----------
        angle : float
            The rotation angle in degrees
        """

        if self.control != "trackball":
            raise NameError("rotateY only works for trackball control")
        self.execute("viewer.controls.rotateY", (angle,))

    def rotate_z(self, angle):
        """
        Rotate CAD obj around z-axis - trackball controls only

        Parameters
        ----------
        angle : float
            The rotation angle in degrees
        """

        if self.control != "trackball":
            raise NameError("rotateZ only works for trackball control")
        self.execute("viewer.controls.rotateZ", (angle,))

    def rotate_up(self, angle):
        """
        Rotate CAD obj up (positive angle) and down (negative angle) - orbit controls only

        Parameters
        ----------
        angle : float
            The rotation angle in degrees
        """

        if self.control != "orbit":
            raise NameError("rotateUp only works for orbit control")
        self.execute("viewer.controls.rotateUp", (angle,))

    def rotate_left(self, angle):
        """
        Rotate CAD obj to the left (positive angle) and right (negative angle) - orbit controls only

        Parameters
        ----------
        angle : float
            The rotation angle in degrees
        """

        if self.control != "orbit":
            raise NameError("rotateLeft only works for orbit control")
        self.execute("viewer.controls.rotateLeft", (angle,))

    #
    # Exports
    #

    def export_html(self, filename="cadquery.html", title="CadQuery"):
        if self.widget.title != None:
            raise RuntimeError("Export_html does not work with sidecar. Show the object again in a cell viewer")

        pinning = self.pinning
        self.pinning = False

        embed_minimal_html(filename, title=title, views=[self.widget], state=dependency_state(self.widget))

        self.pinning = pinning

    #
    # Custom message handling
    #

    def execute(self, method, args=None):
        """
        Execute a method of a Javascript object

        Parameters
        ----------
        method : string
            A 'CadViewer' object based Javascrip object path, e.g. `abc.def[3].method(args)` where `abc.def[3]` is the
            object notation relative to the 'CadViewer' object and `method` is the method to call
        args : list of any
            The arguments passed to `abc.def[3].method(args)`
        """

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

    def dump_model(self, shapes=False):
        print(
            dedent(
                f"""
                        DISPLAY
                title:              {self.widget.title}
                anchor:             {self.widget.anchor}
                cad_width:          {self.widget.cad_width}
                height:             {self.widget.height}
                tree_width:         {self.widget.tree_width}
                theme:              {self.widget.theme}
                pinning:            {self.widget.pinning}

                            SHAPES
                shapes:             {self.widget.shapes if shapes else "... (set shapes=True)"}
                states:             {self.widget.states}
                tracks:             {self.widget.tracks}
                            
                            RENDERER
                normal_len:         {self.widget.normal_len}
                default_edge_color: {self.widget.default_edge_color}
                default_opacity:    {self.widget.default_opacity}
                ambient_intensity:  {self.widget.ambient_intensity}
                direct_intensity:   {self.widget.direct_intensity}
                            
                            VIEWER
                timeit:             {self.widget.timeit}
                tools:              {self.widget.tools}
                ortho:              {self.widget.ortho}
                control:            {self.widget.control}
                axes:               {self.widget.axes}
                axes0:              {self.widget.axes0}
                grid:               {self.widget.grid}
                ticks:              {self.widget.ticks}
                transparent:        {self.widget.transparent}
                black_edges:        {self.widget.black_edges}
                tab:                {self.widget.tab}
                clip_intersection:  {self.widget.clip_intersection}
                clip_planes:        {self.widget.clip_planes}
                clip_normal_0:      {self.widget.clip_normal_0}
                clip_normal_1:      {self.widget.clip_normal_1}
                clip_normal_2:      {self.widget.clip_normal_2}
                clip_slider_0:      {self.widget.clip_slider_0}
                clip_slider_1:      {self.widget.clip_slider_1}
                clip_slider_2:      {self.widget.clip_slider_2}
                reset_camera:       {self.widget.reset_camera}
                position:           {self.widget.position}
                quaternion:         {self.widget.quaternion}
                target:             {self.widget.target}
                zoom:               {self.widget.zoom}
                position0:          {self.widget.position0}
                quaternion0:        {self.widget.quaternion0}
                target0:            {self.widget.target0}
                zoom0:              {self.widget.zoom0}
                zoom_speed:         {self.widget.zoom_speed}
                pan_speed:          {self.widget.pan_speed}
                rotate_speed:       {self.widget.rotate_speed}
                animation_speed:    {self.widget.animation_speed}
                state_updates:      {self.widget.state_updates}
                lastPick:           {self.widget.lastPick}

                            INTERNAL
                result:             {self.widget.result}
                disposed:           {self.widget.disposed}
                initialize:         {self.widget.initialize}
                js_debug:           {self.widget.js_debug}
                image_id:           {self.widget.image_id}
                """
            )
        )
