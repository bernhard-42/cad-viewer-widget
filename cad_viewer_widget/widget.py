# pylint: disable=too-many-lines
"""This module is the Python part of the CAD Viewer widget"""

import base64
import orjson
from pathlib import Path
from textwrap import dedent

import numpy as np

import ipywidgets as widgets
from ipywidgets.embed import embed_minimal_html, dependency_state

from traitlets import (
    Unicode,
    Dict,
    List,
    Tuple,
    Integer,
    Float,
    Any,
    Bool,
    Enum,
    Callable,
    observe,
)
from IPython.display import HTML, update_display
from pyparsing import ParseException

from .utils import get_parser, to_json, bsphere, normalize


VIEWER = {}
COLLAPSE = {
    "R": "R",
    "C": "C",
    "E": "E",
    "1": "1",
}


def _set_collapse(collapse):
    # Allows injecting Collapse enum. Import would lead to circular import
    global COLLAPSE
    for k, v in collapse.items():
        COLLAPSE[k] = v


def get_viewer_by_id(id_):
    return VIEWER.get(id_)


def get_viewers_by_id():
    return VIEWER


# pylint: disable=too-few-public-methods
class AnimationTrack:
    # pylint: disable=line-too-long
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
class CadViewerWidget(
    widgets.Output
):  # pylint: disable-msg=too-many-instance-attributes
    """The CAD Viewer widget."""

    _view_name = Unicode("CadViewerView").tag(sync=True)
    _model_name = Unicode("CadViewerModel").tag(sync=True)
    _view_module = Unicode("cad-viewer-widget").tag(sync=True)
    _model_module = Unicode("cad-viewer-widget").tag(sync=True)
    _view_module_version = Unicode("3.0.2").tag(sync=True)
    _model_module_version = Unicode("3.0.2").tag(sync=True)

    #
    # Internal id
    #
    id = Unicode(allow_none=True).tag(sync=True)
    "unicode uuid4 string serving as internal id of the widget"

    #
    # Display traits
    #

    title = Unicode(allow_none=True).tag(sync=True)
    "unicode string of the title of the sidecar to be used. None means CAD view will be opened in cell"

    anchor = Unicode(allow_none=True).tag(sync=True)
    "unicode string whether to add a view to the right sidebar ('right') or as a tab to the main window ('tab')"

    cad_width = Integer().tag(sync=True)
    "unicode string: Width of the canvas element for cell viewer and right sidecar"

    height = Integer(allow_none=True).tag(sync=True)
    "int: Height of the canvas element for cell viewer"

    tree_width = Integer(allow_none=True).tag(sync=True)
    "int: Width of the navigation tree element"

    aspect_ratio = Float(allow_none=True, default_value=None).tag(sync=True)
    "float: aspect ratio for sidecar"

    theme = Unicode(allow_none=True).tag(sync=True)
    "unicode string: UI theme, can be 'dark' or 'light' (default)"

    pinning = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to show the pin a png button or not"

    new_tree_behavior = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to  hide the complete shape when clicking on the eye (True) or only the faces (False)"

    #
    # Viewer traits
    #

    keymap = Dict(Tuple(Unicode(), Unicode()), allow_none=True).tag(sync=True)
    "dict: Mapping of the modifier keys, defaults to {'shift': 'shiftKey', 'ctrl': 'ctrlKey', 'meta': 'metaKey'}"

    shapes = Dict(allow_none=True).tag(sync=True, to_json=to_json)
    "unicode: Serialized nested tessellated shapes"

    states = Dict(Tuple(Integer(), Integer()), allow_none=True).tag(sync=True)
    # pylint: disable=line-too-long
    "dict: State of the nested cad objects, key = object path, value = 2-dim tuple of 0/1 (hidden/visible) for object and edges"

    state_updates = Dict(Tuple(Integer(), Integer()), allow_none=True).tag(sync=True)
    # pylint: disable=line-too-long
    "dict: Updates to the state of the nested cad objects, key = object path, value = 2-dim tuple of 0/1 (hidden/visible) for object and edges"

    tracks = List(allow_none=True).tag(sync=True)
    # pylint: disable=line-too-long
    "unicode: Serialized list of animation track arrays, see [AnimationTrack.to_array](/widget.html#cad_viewer_widget.widget.AnimationTrack.to_array)"

    timeit = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to output timing info to the browser console (True) or not (False)"

    tools = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to show CAD tools (True) or not (False)"

    glass = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to use the glass mode (CAD navigation as transparent overlay) or not"

    ortho = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to use orthographic view (True) or perspective view (False)"

    control = Unicode().tag(sync=True)
    "unicode: Whether to use trackball controls ('trackball') or orbit controls ('orbit')"

    up = Unicode().tag(sync=True)
    "unicode: Whether camera up direction is Z ('Z') or Y ('Y') or the legacy Z orientation ('L')"

    axes = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to show coordinate axes (True) or not (False)"

    axes0 = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to center coordinate axes at the origin [0,0,0] (True) or at the CAD object center (False)"

    grid = Tuple(Bool(), Bool(), Bool(), allow_none=True).tag(sync=True)
    "tuple: Whether to show the grids for `xy`, `xz`, `yz`."

    center_grid = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to center the grid at (0, 0, 0) not (False)"

    explode = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to show the explode menu or not (False)"

    ticks = Integer(allow_none=True).tag(sync=True)
    "integer: Hint for the number of ticks for the grids (will be adjusted for nice intervals)"

    transparent = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to show the CAD objects transparently (True) or not (False)"

    black_edges = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to shows the edges in black (True) or not(False)"

    collapse = Enum(["1", "R", "E", "C"], allow_none=True, default_value=None).tag(
        sync=True
    )
    # pylint: disable=line-too-long
    "Enum Collapse: Collapse CAD tree ('1': collapse all leaf nodes, 'R': expand root level only, 'C': collapse all nodes, 'E': expand all nodes)"

    normal_len = Float(allow_none=True).tag(sync=True)
    "float: If > 0, the vertex normals will be rendered with the length given be this parameter"

    default_edgecolor = Unicode(allow_none=True, default_value=None).tag(sync=True)
    "unicode: The default edge color in web format, e.g. '#ffaa88'"

    default_opacity = Float(allow_none=True, default_value=None).tag(sync=True)
    "unicode: The default opacity for transparent objects"

    ambient_intensity = Float(allow_none=True, default_value=None).tag(sync=True)
    "float: The intensity of the ambient light"

    direct_intensity = Float(allow_none=True, default_value=None).tag(sync=True)
    "float: The intensity of the direct light"

    metalness = Float(allow_none=True, default_value=None).tag(sync=True)
    "float: The degree of metalness"

    roughness = Float(allow_none=True, default_value=None).tag(sync=True)
    "float: The degree of roughness"

    #
    # Generic UI traits
    #

    tab = Enum(["tree", "clip", "material"], allow_none=True).tag(sync=True)
    "unicode: Whether to show the navigation tree ('tree'), clipping UI ('clip') or material UI ('material')"

    clip_intersection = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to use intersection clipping (True) or not (False)"

    clip_planes = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to show colored clipping planes (True) or not (False)"

    clip_normal_0 = Tuple(
        Float(), Float(), Float(), allow_none=True, default_value=None
    ).tag(sync=True)
    "tuple: Normal of clipping plane 1 as a 3-dim tuple of float (x,y,z)"

    clip_normal_1 = Tuple(
        Float(), Float(), Float(), allow_none=True, default_value=None
    ).tag(sync=True)
    "tuple: Normal of clipping plane 2 as a 3-dim tuple of float (x,y,z)"

    clip_normal_2 = Tuple(
        Float(), Float(), Float(), allow_none=True, default_value=None
    ).tag(sync=True)
    "tuple: Normal of clipping plane 3 as a 3-dim tuple of float (x,y,z)"

    clip_slider_0 = Float(allow_none=True, default_value=None).tag(sync=True)
    "float: Slider value of clipping plane 1"

    clip_slider_1 = Float(allow_none=True, default_value=None).tag(sync=True)
    "float: Slider value of clipping plane 2"

    clip_slider_2 = Float(allow_none=True, default_value=None).tag(sync=True)
    "float: Slider value of clipping plane 3"

    clip_object_colors = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to show colored clipping caps in object color (True) or not (False)"

    reset_camera = Enum(
        ["reset", "keep", "center"], allow_none=True, default_value=None
    ).tag(sync=True)
    "Enum Camera: Whether to reset camera (reset) or not (keep or center keep orientation but center the camera)"

    position = Tuple(Float(), Float(), Float(), allow_none=True).tag(sync=True)
    "tuple: Position of the camera as a 3-dim tuple of float (x,y,z)"

    quaternion = Tuple(Float(), Float(), Float(), Float(), allow_none=True).tag(
        sync=True
    )
    "tuple: Rotation of the camera as 4-dim quaternion (x,y,z,w)"

    target = Tuple(Float(), Float(), Float(), allow_none=True).tag(sync=True)
    "tuple: Camera target to look at as 3-dim tuple (x,y,z)"

    zoom = Float(allow_none=True).tag(sync=True)
    "float: Zoom value of the camera"

    zoom_speed = Float(allow_none=True).tag(sync=True)
    "float: Speed of zooming with the mouse"

    pan_speed = Float(allow_none=True).tag(sync=True)
    "float: Speed of panning with the mouse"

    rotate_speed = Float(allow_none=True).tag(sync=True)
    "float: Speed of rotation with the mouse"

    animation_speed = Float(allow_none=True).tag(sync=True)
    "float: Animation speed"

    #
    # Read only traitlets
    #

    lastPick = Dict(
        key_trait=Unicode(), value_trait=Any(), allow_none=True, read_only=True
    ).tag(sync=True)
    "dict: Describes the last picked element of the CAD view"

    result = Unicode(allow_none=True, read_only=True).tag(sync=True)
    "unicode string: JSON serialized result from Javascript"

    #
    # Internal traitlets
    #

    disposed = Bool(default=False, allow_none=True, default_value=None).tag(sync=True)
    "unicode string: Whether the Javascript viewer is disposed"

    initialize = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: internally used to control initialization of view. Do not use!"

    debug = Bool(allow_none=True, default_value=None).tag(sync=True)
    "bool: Whether to show infos in the browser console (True) or not (False)"

    image_id = Unicode(allow_none=True).tag(sync=True)
    "unicode string: the id of the image tag to use for pin as png"

    activeTool = Unicode(allow_none=True).tag(sync=True)
    "unicode: Active measurement tool"

    selectedShapeIDs = List(allow_none=True).tag(sync=True)
    "list: List of selected object paths"

    measure = Dict(allow_none=True).tag(sync=True)
    "list: JSON of calculated measures"

    measure_callback = Callable(allow_none=True)

    @observe("result")
    def func(self, change):
        """
        Handles changes in the observed trait and processes the new data accordingly.

        Parameters:
        change (dict): A dictionary containing information about the change.
                       Expected to have a "new" key with a JSON string value.

        The function performs the following actions based on the content of the "new" key:
        - If "display_id" is present in the data, it updates an HTML display with an image.
        - If "display_id" is not present and `self.test_func` is callable, it calls `self.test_func` with the decoded image data.
        - If "display_id" is not present and `self.test_func` is not callable, it writes the decoded image data to a file specified by "filename".
        """
        if change["new"] is not None:
            data = orjson.loads(change["new"])

            if data.get("display_id") is not None:
                html = f"""<img src="{data['src']}" width="{data['width']}px" height="{data['height']}px"/>"""
                update_display(HTML(html), display_id=data["display_id"])
            else:
                if self.test_func is not None and callable(self.test_func):
                    # pylint: disable=not-callable
                    self.test_func(base64.b64decode(data["src"].split(",")[1]))
                else:
                    with open(data["filename"], "wb") as fd:
                        fd.write(base64.b64decode(data["src"].split(",")[1]))

    @observe("activeTool")
    def active_tool(self, change):
        if change["new"]:
            status, result = self.measure_callback(
                self.id, {"activeTool": change["new"]}
            )

    @observe("selectedShapeIDs")
    def selected_shape_ids(self, change):
        if change["new"]:
            status, result = self.measure_callback(
                self.id, {"selectedShapeIDs": change["new"]}
            )
            if status == 200:
                result = orjson.loads(result)
                if result.get("success") is not None:
                    self.measure = result["success"]
                elif result.get("error") is not None:
                    print("Error:", result["error"])
            else:
                print("Error:", result)


class CadViewer:
    # pylint: disable=line-too-long
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
    glass : bool, default: False
        Whether to use glass mode (True) or not (False)
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
        aspect_ratio=0.75,
        theme="browser",
        glass=False,
        tools=True,
        pinning=False,
        title=None,
        anchor=None,
        new_tree_behavior=True,
        id_=None,
    ):
        if cad_width < 780:
            raise ValueError("Ensure cad_width >= 780")
        if tree_width < 240:
            raise ValueError("Ensure tree_width >= 240")

        self.widget = CadViewerWidget(
            cad_width=cad_width,
            height=height,
            tree_width=tree_width,
            aspect_ratio=aspect_ratio,
            theme=theme,
            glass=glass,
            tools=tools,
            pinning=pinning,
            title=title,
            anchor=anchor,
            new_tree_behavior=new_tree_behavior,
            up="Z",
            control="trackball",
            id=id_,
        )
        self.widget.test_func = None
        self.msg_id = 0
        self.parser = get_parser()

        self.empty = True
        self._splash = True
        self.tracks = []

    def register_viewer(self):
        global VIEWER
        VIEWER[self.widget.id] = self

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
        tracks=None,
        # render options
        normal_len=0,
        default_edgecolor="#707070",
        default_opacity=0.5,
        ambient_intensity=1.0,
        direct_intensity=1.1,
        metalness=0.3,
        roughness=0.65,
        # viewer options
        tools=None,
        glass=None,
        new_tree_behavior=None,
        control=None,
        up=None,
        ortho=True,
        axes=None,
        axes0=None,
        grid=None,
        center_grid=None,
        explode=None,
        ticks=10,
        transparent=None,
        black_edges=None,
        collapse=None,
        position=None,
        quaternion=None,
        target=None,
        zoom=None,
        reset_camera=None,
        clip_slider_0=None,
        clip_slider_1=None,
        clip_slider_2=None,
        clip_normal_0=None,
        clip_normal_1=None,
        clip_normal_2=None,
        clip_intersection=None,
        clip_planes=None,
        clip_object_colors=None,
        zoom_speed=None,
        pan_speed=None,
        rotate_speed=None,
        timeit=False,
        debug=False,
        _is_logo=False,
    ):
        # pylint: disable=line-too-long
        """
        Adding shapes to the CAD view

        Parameters
        ----------
        shapes : dict
            Nested tessellated shapes
        tracks : list or tuple, default None
            List of animation track arrays, see [AnimationTrack.to_array](/widget.html#cad_viewer_widget.widget.AnimationTrack.to_array)
        title: str, default: None
            Name of the title view to display the shapes.
        ortho : bool, default True
            Whether to use orthographic view (True) or perspective view (False)
        cad_width : int, default: None
            Width of the canvas element
        height : int, default: None
            Height of the canvas element
        tree_width : int, default: None
            Width of the navigation tree element
        tools : bool, default: None
            Whether to show CAD tools (True) or not (False)
        glass : bool, default: None
            Whether to use glass mode (True) or not (False)
        control : string, default 'trackball'
            Whether to use trackball controls ('trackball') or orbit controls ('orbit')
        up : string, default 'Z'
            Whether camera up direction is Z ('Z') or Y ('Y') or the lagacy Z orientation ('L')
        axes : bool, default False
            Whether to show coordinate axes (True) or not (False)
        axes0 : bool, default False
            Whether to center coordinate axes at the origin [0,0,0] (True) or at the CAD object center (False)
        grid : 3-dim list of bool, default None
            Whether to show the grids for `xy`, `xz`, `yz` (`None` means `(False, False, False)`)
        explode : bool, default: None
            Whether to show the explode widget (True) or not (False)
        ticks : int, default 10
            Hint for the number of ticks for the grids (will be adjusted for nice intervals)
        transparent : bool, default False
            Whether to show the CAD objects transparently (True) or not (False)
        black_edges : bool, default False
            Whether to shows the edges in black (True) or not(False)
        collapse : int, default 0
            Collapse CAD tree (1: collapse nodes with single leaf, 2: collapse all nodes)
        normal_Len : int, default 0
            If > 0, the vertex normals will be rendered with the length given be this parameter
        default_edgecolor : string, default "#707070"
            The default edge color in web format, e.g. '#707070'
        default_opacity : float, default 0.5
            The default opacity level for transparency between 0.0 an 1.0
        ambient_intensity : float, default 1.0
            The intensity of the ambient light
        direct_intensity : float, default 1.1
            The intensity of the direct light
        metalness : float, default 0.3
            The degree of material metalness
        roughness : float, default 0.65
            The degree of material roughness
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
            "loc": None,  # would be (<position>, <quaternion>), e.g. ([0,0,0), (0,0,0,1)]),
            "bb": {
                "xmin": -0.5, "xmax": 0.5,
                "ymin": -0.5, "ymax": 0.5,
                "zmin": -0.5, "zmax": 0.5
            }
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
                "renderback": false
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
            "renderback": false
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
            "renderback": false
            "shape": <EdgeList>
        }

        Vertices := {
            "id": "</path/to/<name>>",
            "name": "<name>",
            "type": "vertices",
            "color": "#ffffff",
            "size": 6
            "shape": <VectorList>
        }
        """

        if control == "orbit" and quaternion is not None:
            raise ValueError(
                "Camera quaternion cannot be used with Orbit camera control"
            )

        if control == "trackball" and position is not None and quaternion is None:
            raise ValueError(
                "For Trackball camera control, position paramater also needs quaternion parameter"
            )

        if up not in ["Z", "Y", "L"]:
            raise ValueError(f"Camera up value '{up}' can only be Y or Z or L")

        if grid is None:
            grid = [False, False, False]

        self.widget.debug = debug
        self.widget.initialize = True

        # set shapes to None so that the same object can be shown again
        self.widget.shapes = None

        if self.widget.aspect_ratio is None:
            self.widget.aspect_ratio = 0.75

        with self.widget.hold_trait_notifications():
            self.widget.shapes = shapes

            self.widget.default_edgecolor = default_edgecolor
            self.widget.default_opacity = default_opacity
            self.widget.ambient_intensity = ambient_intensity
            self.widget.direct_intensity = direct_intensity
            self.widget.metalness = metalness
            self.widget.roughness = roughness
            self.widget.normal_len = normal_len
            self.widget.control = control
            self.widget.up = up
            if tools is not None:
                self.widget.tools = tools
            if glass is not None:
                self.widget.glass = glass
            self.widget.new_tree_behavior = new_tree_behavior
            self.widget.axes = axes
            self.widget.axes0 = axes0
            self.widget.grid = grid
            self.widget.center_grid = center_grid
            self.explode = explode
            self.widget.ticks = ticks
            self.widget.ortho = ortho
            self.widget.transparent = transparent
            self.widget.black_edges = black_edges
            self.widget.collapse = collapse
            self.widget.reset_camera = reset_camera
            self.widget.position = position
            self.widget.quaternion = quaternion
            self.widget.target = target
            self.widget.zoom = zoom
            self.widget.zoom_speed = zoom_speed
            self.widget.pan_speed = pan_speed
            self.widget.rotate_speed = rotate_speed
            self.widget.timeit = timeit
            self.widget.clip_slider_0 = clip_slider_0
            self.widget.clip_slider_1 = clip_slider_1
            self.widget.clip_slider_2 = clip_slider_2
            self.widget.clip_normal_0 = clip_normal_0
            self.widget.clip_normal_1 = clip_normal_1
            self.widget.clip_normal_2 = clip_normal_2
            self.widget.clip_intersection = clip_intersection
            self.widget.clip_planes = clip_planes
            self.widget.clip_object_colors = clip_object_colors

            self.add_tracks(tracks)

        self.widget.initialize = False

        if tools is not None:
            self.widget.tools = tools

        if glass is not None:
            self.widget.glass = glass

        if not _is_logo:
            self._splash = False

    def update_camera_location(self):
        """Sync position, quaternion and zoom of camera to Python"""
        self.execute("updateCamera", [])

    def close(self):
        """
        Close the underlying Javascript viewer
        """
        self.widget.disposed = True

    @property
    def states(self):
        """
        Get the states of the objects in the navigation tree
        """

        return self.widget.states

    def update_states(self, states):
        old_states = self.widget.states.copy()
        new_states = {}
        # validation that path exists
        for k, v in states.items():
            if old_states.get(k) is not None:
                new_states[k] = v
        self.widget.state_updates = new_states

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
    def metalness(self):
        """
        Get or set the CadViewerWidget traitlet `metalness`
        see [CadViewerWidget.direct_intensity](./widget.html#cad_viewer_widget.widget.CadViewerWidget.metalness)
        """

        return self.widget.metalness

    @metalness.setter
    def metalness(self, value):
        self.widget.metalness = value

    @property
    def roughness(self):
        """
        Get or set the CadViewerWidget traitlet `roughness`
        see [CadViewerWidget.direct_intensity](./widget.html#cad_viewer_widget.widget.CadViewerWidget.roughness)
        """

        return self.widget.roughness

    @roughness.setter
    def roughness(self, value):
        self.widget.roughness = value

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
    def center_grid(self):
        """
        Get or set the CadViewerWidget traitlet `center_grid`
        see [CadViewerWidget.grid](./widget.html#cad_viewer_widget.widget.CadViewerWidget.center_grid)
        """

        return self.widget.center_grid

    @center_grid.setter
    def center_grid(self, value):
        self.widget.center_grid = value

    @property
    def explode(self):
        """
        Get or set the CadViewerWidget traitlet `explode`
        see [CadViewerWidget.explode](./widget.html#cad_viewer_widget.widget.CadViewerWidget.explode)
        """

        return self.widget.explode

    @explode.setter
    def explode(self, value):
        self.widget.explode = value

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
    def default_edgecolor(self):
        """
        Get or set the CadViewerWidget traitlet `default_edgecolor`
        see [CadViewerWidget.default_edgecolor](./widget.html#cad_viewer_widget.widget.CadViewerWidget.default_edgecolor)
        """

        return self.widget.default_edgecolor

    @default_edgecolor.setter
    def default_edgecolor(self, value):
        if value.startswith("#"):
            self.widget.default_edgecolor = value
        else:
            self.widget.default_edgecolor = f"#{value}"

    @property
    def default_opacity(self):
        """
        Get or set the CadViewerWidget traitlet `default_opacity`
        see [CadViewerWidget.default_opacity](./widget.html#cad_viewer_widget.widget.CadViewerWidget.default_opacity)
        """

        return self.widget.default_opacity

    @default_opacity.setter
    def default_opacity(self, value):
        self.widget.default_opacity = value

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
    def clip_slider_0(self):
        """
        Get or set the CadViewerWidget traitlet `clip_slider_0`
        see [CadViewerWidget.clip_slider_0](./widget.html#cad_viewer_widget.widget.CadViewerWidget.clip_slider_0)
        """

        return self.widget.clip_slider_0

    @clip_slider_0.setter
    def clip_slider_0(self, value):
        self.widget.clip_slider_0 = value

    @property
    def clip_slider_1(self):
        """
        Get or set the CadViewerWidget traitlet `clip_slider_1`
        see [CadViewerWidget.clip_slider_1](./widget.html#cad_viewer_widget.widget.CadViewerWidget.clip_slider_1)
        """

        return self.widget.clip_slider_1

    @clip_slider_1.setter
    def clip_slider_1(self, value):
        self.widget.clip_slider_1 = value

    @property
    def clip_slider_2(self):
        """
        Get or set the CadViewerWidget traitlet `clip_slider_2`
        see [CadViewerWidget.clip_slider_2](./widget.html#cad_viewer_widget.widget.CadViewerWidget.clip_slider_2)
        """

        return self.widget.clip_slider_2

    @clip_slider_2.setter
    def clip_slider_2(self, value):
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
    def clip_object_colors(self):
        """
        Get or set the CadViewerWidget traitlet `clip_object_colors`
        see [CadViewerWidget.clip_planes](./widget.html#cad_viewer_widget.widget.CadViewerWidget.clip_object_colors)
        """

        return self.widget.clip_object_colors

    @clip_object_colors.setter
    def clip_object_colors(self, value):
        self.widget.clip_object_colors = value

    @property
    def debug(self):
        """
        Get or set the CadViewerWidget traitlet `debug`
        see [CadViewerWidget.debug](./widget.html#cad_viewer_widget.widget.CadViewerWidget.debug)
        """

        return self.widget.debug

    @debug.setter
    def debug(self, value):
        self.widget.debug = value

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
    def glass(self):
        """
        Get or set the CadViewerWidget traitlet `glass`
        see [CadViewerWidget.tools](./widget.html#cad_viewer_widget.widget.CadViewerWidget.glass)
        """

        return self.widget.glass

    @glass.setter
    def glass(self, value):
        self.widget.glass = value

    @property
    def cad_width(self):
        """
        Get or set the CadViewerWidget traitlet `cad_width`
        see [CadViewerWidget.tools](./widget.html#cad_viewer_widget.widget.CadViewerWidget.cad_width)
        """

        return self.widget.cad_width

    @cad_width.setter
    def cad_width(self, value):
        self.widget.cad_width = value

    @property
    def tree_width(self):
        """
        Get or set the CadViewerWidget traitlet `tree_width`
        see [CadViewerWidget.tools](./widget.html#cad_viewer_widget.widget.CadViewerWidget.tree_width)
        """

        return self.widget.tree_width

    @tree_width.setter
    def tree_width(self, value):
        self.widget.tree_width = value

    @property
    def height(self):
        """
        Get or set the CadViewerWidget traitlet `height`
        see [CadViewerWidget.tools](./widget.html#cad_viewer_widget.widget.CadViewerWidget.height)
        """

        return self.widget.height

    @height.setter
    def height(self, value):
        self.widget.height = value

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

        return self.widget.quaternion

    @quaternion.setter
    def quaternion(self, value):
        if self.widget.control == "orbit":
            print("quaternion controlled internally for orbit control")
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
    def up(self):
        """
        Get or set the CadViewerWidget traitlet `up`
        see [CadViewerWidget.up](./widget.html#cad_viewer_widget.widget.CadViewerWidget.up)
        """

        return self.widget.up

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

    @property
    def collapse(self):
        """
        Get or set the CadViewerWidget traitlet `collapse`
        see [CadViewerWidget.collapse](./widget.html#cad_viewer_widget.widget.CadViewerWidget.collapse)
        """
        return COLLAPSE[self.widget.collapse]

    @collapse.setter
    def collapse(self, value):
        if isinstance(value, str):
            self.widget.collapse = value
        elif isinstance(value, Enum):
            rev_mapping = {v: k for k, v in COLLAPSE.items()}
            self.widget.collapse = rev_mapping[value]
        else:
            raise TypeError(f"Unknown type {type(value)} for collapse")

    @property
    def keymap(self):
        """
        Get or set the CadViewerWidget traitlet `keymap`
        see [CadViewerWidget.keymap](./widget.html#cad_viewer_widget.widget.CadViewerWidget.keymap)
        """
        return self.widget.keymap

    @keymap.setter
    def keymap(self, value):
        self.widget.keymap = value

    @property
    def new_tree_behavior(self):
        """
        Get or set the CadViewerWidget traitlet `new_tree_behavior`
        see [CadViewerWidget.new_tree_behavior](./widget.html#cad_viewer_widget.widget.CadViewerWidget.new_tree_behavior)
        """
        return self.widget.new_tree_behavior

    @new_tree_behavior.setter
    def new_tree_behavior(self, value):
        self.widget.new_tree_behavior = value

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
            raise ValueError(
                f"{track.path} is not a valid subpath of any of {list(paths)}"
            )

        actions = ["t", "tx", "ty", "tz", "q", "rx", "ry", "rz"]
        if not track.action in actions:
            raise ValueError(f"{track.action} is not a valid action {list(actions)}")

        if len(track.times) != len(track.values):
            raise ValueError("Track times and values need to have same length")

        if not all([isinstance(t, (int, float)) for t in track.times]):
            raise ValueError("Time values need to be int or float")

        if track.action in ["tx", "ty", "tz", "rx", "ry", "rz"]:
            if not all([isinstance(t, (int, float)) for t in track.values]):
                raise ValueError(
                    f"Value values need to be int or float for action '{track.action}'"
                )

        if track.action in ["t", "q"]:
            size = 3 if track.action == "t" else 4
            if not all(
                [
                    isinstance(v, (list, tuple))
                    and (len(v) == size)
                    and all([isinstance(x, (int, float)) for x in v])
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
        path = Path(filename)
        if not path.is_absolute():
            path = path.cwd() / path
        print(f"Saving CAD view to {path}")
        self.execute("saveAsPng", str(path))

    #
    # Tab handling
    #

    @property
    def tab(self):
        """
        Get or set the CadViewerWidget traitlet `tab`
        see [CadViewerWidget.tab](./widget.html#cad_viewer_widget.widget.CadViewerWidget.tab)
        """
        return self.widget.tab

    @keymap.setter
    def tab(self, value):
        self.widget.tab = value

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
        """
        Exports the current widget view to an HTML file.

        Parameters:
        filename (str): The name of the HTML file to export. Default is "cadquery.html".
        title (str): The title of the HTML document. Default is "CadQuery".

        Raises:
        RuntimeError: If the widget is displayed in a sidecar.

        Notes:
        - This method temporarily disables pinning while exporting the HTML.
        - The state of the widget is captured and embedded in the HTML file.
        """
        if not (self.widget.title is None or self.widget.title == ""):
            raise RuntimeError(
                "Export_html does not work with sidecar. Show the object again in a cell viewer"
            )

        pinning = self.pinning
        self.pinning = False

        embed_minimal_html(
            filename,
            title=title,
            views=[self.widget],
            state=dependency_state(self.widget),
        )

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
                    "method": path,
                    "args": args,
                }
                self.widget.send(content=content, buffers=None)

                return self.msg_id

        if args is not None and not isinstance(args, (tuple, list)):
            args = [args]
        return wrapper()

    def status(self, all=False):
        """
        Returns the status of the widget with various properties.

        Args:
            shapes (bool): If True, includes the shapes in the status. Defaults to False.

        Returns:
            dict: A dictionary containing the status of the widget
        """
        result = {
            "title": self.widget.title,
            "anchor": self.widget.anchor,
            "cad_width": self.widget.cad_width,
            "height": self.widget.height,
            "tree_width": self.widget.tree_width,
            "theme": self.widget.theme,
            "pinning": self.widget.pinning,
            "states": self.widget.states,
            "tracks": self.widget.tracks,
            "default_edgecolor": self.widget.default_edgecolor,
            "default_opacity": self.widget.default_opacity,
            "ambient_intensity": self.widget.ambient_intensity,
            "direct_intensity": self.widget.direct_intensity,
            "metalness": self.widget.metalness,
            "roughness": self.widget.roughness,
            "tools": self.widget.tools,
            "glass": self.widget.glass,
            "ortho": self.widget.ortho,
            "control": self.widget.control,
            "up": self.widget.up,
            "axes": self.widget.axes,
            "axes0": self.widget.axes0,
            "grid": self.widget.grid,
            "center_grid": self.widget.center_grid,
            "explode": self.widget.explode,
            "ticks": self.widget.ticks,
            "transparent": self.widget.transparent,
            "black_edges": self.widget.black_edges,
            "collapse": self.widget.collapse,
            "tab": self.widget.tab,
            "clip_intersection": self.widget.clip_intersection,
            "clip_object_colors": self.widget.clip_object_colors,
            "clip_planes": self.widget.clip_planes,
            "clip_normal_0": self.widget.clip_normal_0,
            "clip_normal_1": self.widget.clip_normal_1,
            "clip_normal_2": self.widget.clip_normal_2,
            "clip_slider_0": self.widget.clip_slider_0,
            "clip_slider_1": self.widget.clip_slider_1,
            "clip_slider_2": self.widget.clip_slider_2,
            "reset_camera": self.widget.reset_camera,
            "position": self.widget.position,
            "quaternion": self.widget.quaternion,
            "target": self.widget.target,
            "zoom": self.widget.zoom,
            "zoom_speed": self.widget.zoom_speed,
            "pan_speed": self.widget.pan_speed,
            "rotate_speed": self.widget.rotate_speed,
            "animation_speed": self.widget.animation_speed,
            "lastPick": self.widget.lastPick,
        }
        if all:
            result.update(
                {
                    "keymap": self.widget.keymap,
                    "shapes": self.widget.shapes,
                    "normal_len": self.widget.normal_len,
                    "timeit": self.widget.timeit,
                    "new_tree_behavior": self.widget.new_tree_behavior,
                }
            )
        return {k: v for k, v in result.items() if v is not None and v != {}}

    def dump_model(self, shapes=False):
        """
        Dumps the status of the widget with various properties.

        Args:
            shapes (bool): If True, includes the shapes in the status. Defaults to False.
        """
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
                default_edgecolor:      {self.widget.default_edgecolor}
                default_opacity:    {self.widget.default_opacity}
                ambient_intensity:  {self.widget.ambient_intensity}
                direct_intensity:   {self.widget.direct_intensity}
                metalness:          {self.widget.metalness}
                roughness:          {self.widget.roughness}              
                            
                            VIEWER
                timeit:             {self.widget.timeit}
                tools:              {self.widget.tools}
                glass:              {self.widget.glass}
                ortho:              {self.widget.ortho}
                control:            {self.widget.control}
                up:                 {self.widget.up}
                axes:               {self.widget.axes}
                axes0:              {self.widget.axes0}
                grid:               {self.widget.grid}
                center_grid:        {self.widget.center_grid}
                explode:            {self.widget.explode}
                ticks:              {self.widget.ticks}
                transparent:        {self.widget.transparent}
                black_edges:        {self.widget.black_edges}
                collapse:           {self.widget.collapse}
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
                zoom_speed:         {self.widget.zoom_speed}
                pan_speed:          {self.widget.pan_speed}
                rotate_speed:       {self.widget.rotate_speed}
                animation_speed:    {self.widget.animation_speed}
                lastPick:           {self.widget.lastPick}
                keymap:             {self.widget.keymap}
                new_tree_behavior:  {self.widget.new_tree_behavior}

                            INTERNAL
                result:             {self.widget.result}
                disposed:           {self.widget.disposed}
                initialize:         {self.widget.initialize}
                debug:              {self.widget.debug}
                image_id:           {self.widget.image_id}
                """
            )
        )
