const typesToArray = {
  uint32: Uint32Array,
  float32: Float32Array
};

function decode(s) {
  function convert(obj) {
    if (obj.dtype != null) {
      return new typesToArray[obj.dtype](obj.buffer.buffer);
    } else {
      return obj;
    }
  }

  function walk(obj) {
    var type = null;
    for (var attr in obj) {
      if (attr === "parts") {
        for (var i in obj.parts) {
          walk(obj.parts[i]);
        }
      } else if (attr === "type") {
        type = obj.type;
      } else if (attr == "shape") {
        if (type === "shapes") {
          obj.shape.vertices = convert(obj.shape.vertices);
          obj.shape.normals = convert(obj.shape.normals);
          obj.shape.triangles = convert(obj.shape.triangles);
          obj.shape.edges = convert(obj.shape.edges);
        } else {
          obj.shape = convert(obj.shape);
        }
      }
    }
  }
  walk(s);
}

export { decode };
