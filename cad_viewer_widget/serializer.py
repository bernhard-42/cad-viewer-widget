import zlib
from base64 import b64encode
import numpy as np


def default(obj):
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


# data = json.dumps(shape, default=default)