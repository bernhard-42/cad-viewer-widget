"""Utility functions"""

import zlib
from base64 import b64encode
import numpy as np
from pyparsing import Literal, Word, alphanums, nums, delimitedList, ZeroOrMore


def serializer(obj):
    """Serialize numpy nested arrays"""

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
    """Check variable type"""
    if isinstance(var, types):
        return var
    else:
        raise ValueError(f"Variable {name} should be of type {types}, but is {type(var)}")


def check_list(name, var, types, length):
    """Check type of list elements"""

    if isinstance(var, (list, tuple)) and len(var) == length and all(isinstance(v, types) for v in var):
        return var
    else:
        raise ValueError(f"Variable {name} should be a {length} dim list of type {types}, but is {var}")


def get_parser():
    """A parser for nested json objects"""
    dot = Literal(".").suppress()
    lbrack = Literal("[").suppress()
    rbrack = Literal("]").suppress()
    integer = Word(nums)
    index = lbrack + delimitedList(integer) + rbrack
    obj = Word(alphanums + "_$") + ZeroOrMore(index)
    return obj + ZeroOrMore(dot + obj)
