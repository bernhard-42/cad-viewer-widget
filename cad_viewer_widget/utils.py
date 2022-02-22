"""Utility functions"""

import numpy as np
from pyparsing import Literal, Word, alphanums, nums, delimitedList, ZeroOrMore


def to_json(value, widget):
    def walk(obj):
        if isinstance(obj, (tuple, list)):
            return obj

        rv = {}
        
        for k,v in obj.items():
            if isinstance(v, np.ndarray):
                if str(v.dtype) in ('int32', 'int64', 'uint64'):
                    v = v.astype("uint32", order='C')  # force uint triangles
                elif not v.flags['C_CONTIGUOUS']:
                    v = np.ascontiguousarray(v)
                v = v.ravel()
                rv[k] = {
                    'shape': v.shape,
                    'dtype': str(v.dtype),
                    'buffer': memoryview(v)
                }
            elif isinstance(v, dict):
                rv[k] = walk(v)
            elif isinstance(v, (tuple, list)):
                rv[k] = [walk(el) for el in v]
            else:
                rv[k] = v
        return rv

    if value is None:
        return None
    
    return walk(value)


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
            "target",
            "zoom",
            "reset_camera",
            "zoom_speed",
            "pan_speed",
            "rotate_speed",
            "timeit",
            "js_debug",
        ]
    }
