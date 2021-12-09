"""Utility functions"""

import zlib
from base64 import b64encode
import numpy as np
from pyparsing import Literal, Word, alphanums, nums, delimitedList, ZeroOrMore


def numpyify(obj):
    """Replace all arrays with numpy ndarrays. They will be serialized with compression"""
    result = {}
    for k, v in obj.items():
        if isinstance(v, dict):
            result[k] = numpyify(v)
        elif k in ["vertices", "normals", "edges"]:
            result[k] = np.asarray(v, dtype=np.float32)
        elif k in ["triangles"]:
            result[k] = np.asarray(v, dtype=np.int32).reshape(-1, 3)
        elif k == "parts":
            result[k] = [numpyify(el) for el in v]
        elif obj.get("type") in ["edges", "vertices"] and k == "shape":
            result[k] = np.asarray(v, dtype=np.float32)
        else:
            result[k] = v
    return result


def serializer(obj):
    """
    Serialize objects and arrays with converting numpy 64 bit floats/int into 32 bit equivalent values for threejs

    Parameters
    ----------
    obj: dict
        Nested dict with numpy arrays
    """

    def compress(obj, dtype):
        cobj = zlib.compress(obj.reshape(-1).astype(dtype).tobytes(order="C"))
        return b64encode(cobj).decode()

    if type(obj).__module__ == np.__name__:
        if isinstance(obj, np.ndarray):
            if obj.dtype in (np.float32, np.float64):
                return ("_f32", obj.shape, compress(obj, "float32"))
            elif obj.dtype in (np.int32, np.int64):
                return ("_i32", obj.shape, compress(obj, "int32"))
            else:
                raise Exception("unknown numpy type")
        else:
            return obj.item()
    raise TypeError("Unknown type:", type(obj))


def check(name, var, types):
    """
    Check variable type

    Parameters
    ----------
    name : string
        Name of the variable to check
    var : any
        Value of the variable
    types
        Allowed Python types
    """

    if isinstance(var, types):
        return var
    else:
        raise ValueError(f"Variable {name} should be of type {types}, but is {type(var)}")


def check_list(name, var, types, length):
    """
    Check type of list elements

    Parameters
    ----------
    name : string
        Name of the variable to check
    var : any
        List value of the variable
    types
        Allowed Python types for every element of the list
    length
        Required length of the list
    """

    if isinstance(var, (list, tuple)) and len(var) == length and all(isinstance(v, types) for v in var):
        return var
    else:
        raise ValueError(f"Variable {name} should be a {length} dim list of type {types}, but is {var}")


def get_parser():
    """
    A parser for nested json objects

    Only used internally to parse Javascript object paths
    """

    dot = Literal(".").suppress()
    lbrack = Literal("[").suppress()
    rbrack = Literal("]").suppress()
    integer = Word(nums)
    index = lbrack + delimitedList(integer) + rbrack
    obj = Word(alphanums + "_$") + ZeroOrMore(index)
    return obj + ZeroOrMore(dot + obj)


def display_args(config):
    return {
        k: v
        for k, v in config.items()
        if k
        in [
            "cad_width",
            "height",
            "tree_width",
            "theme",
            "pinning",
        ]
    }


def viewer_args(config):
    return {
        k: v
        for k, v in config.items()
        if k
        in [
            "default_edge_color",
            "default_opacity",
            "ambient_intensity",
            "direct_intensity",
            "normal_len",
            "control",
            "tools",
            "ticks",
            "axes",
            "axes0",
            "grid",
            "ortho",
            "transparent",
            "black_edges",
            "clipIntersection",
            "clipPlaneHelpers",
            "clipNormal",
            "position",
            "quaternion",
            "zoom",
            "reset_camera",
            "zoom_speed",
            "pan_speed",
            "rotate_speed",
            "timeit",
        ]
    }
