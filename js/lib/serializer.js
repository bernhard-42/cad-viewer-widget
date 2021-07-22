import pako from "pako";
import { Base64 } from "js-base64";

function reshape(arr, shape) {
  function chunk(arr, len) {
    var chunks = [];
    var i = 0;

    while (i < arr.length) {
      chunks.push(Array.from(arr.slice(i, (i += len))));
    }
    return chunks;
  }

  var d = shape.pop();
  while (d) {
    arr = chunk(arr, d);
    d = shape.pop();
  }
  return arr;
}

function _decompress(b64String) {
  return pako.inflate(Base64.toUint8Array(b64String));
}

function _isFloat32Array(obj) {
  return Array.isArray(obj) && obj.length == 3 && obj[0] == "_f32";
}

function _isInt32Array(obj) {
  return Array.isArray(obj) && obj.length == 3 && obj[0] == "_i32";
}

function _decodeObject(v, ArrayClass, flat) {
  // flat == true:  returns flat typed array (Float32Array or Int32Array)
  // flat == false: returns nested javascript array without types
  var buf = _decompress(v[2]);
  if (flat) {
    return new ArrayClass(buf.buffer);
  } else {
    var targetLength = v[1][0];
    var shape = v[1].slice(1);
    var arr = reshape(new ArrayClass(buf.buffer), shape);
    if (arr.length == targetLength) {
      return arr;
    } else {
      console.error("wrong shape provided");
      return null;
    }
  }
}

function _decodeCompressedArray(flat) {
  return (k, v) => {
    if (_isFloat32Array(v)) {
      return _decodeObject(v, Float32Array, flat);
    } else if (_isInt32Array(v)) {
      return _decodeObject(v, Int32Array, flat);
    } else {
      return v;
    }
  };
}

function decode(data, flat) {
  return JSON.parse(data, _decodeCompressedArray(flat));
}

export { decode };
