import math
import zlib
from base64 import b64encode
import numpy as np


def serializer(obj):
    def compress(obj, dtype):
        c = zlib.compress(obj.reshape(-1).astype(dtype).tobytes(order="C"))
        return b64encode(c).decode()

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


def rotate_x(vector, angle):
    angle = rad(angle)
    mat = np.array(
        [
            [1, 0, 0],
            [0, math.cos(angle), -math.sin(angle)],
            [0, math.sin(angle), math.cos(angle)],
        ]
    )
    return tuple(np.matmul(mat, vector))


def rad(deg):
    return deg / 180.0 * math.pi


def rotate_y(vector, angle):
    angle = rad(angle)
    mat = np.array(
        [
            [math.cos(angle), 0, math.sin(angle)],
            [0, 1, 0],
            [-math.sin(angle), 0, math.cos(angle)],
        ]
    )
    return tuple(np.matmul(mat, vector))


def rotate_z(vector, angle):
    angle = rad(angle)
    mat = np.array(
        [
            [math.cos(angle), -math.sin(angle), 0],
            [math.sin(angle), math.cos(angle), 0],
            [0, 0, 1],
        ]
    )
    return tuple(np.matmul(mat, vector))


def rotate(vector, angle_x=0, angle_y=0, angle_z=0):
    v = tuple(vector)
    if angle_z != 0:
        v = rotate_z(v, angle_z)
    if angle_y != 0:
        v = rotate_y(v, angle_y)
    if angle_x != 0:
        v = rotate_x(v, angle_x)
    return v