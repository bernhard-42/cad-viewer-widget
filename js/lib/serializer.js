const typesToArray = {
  uint32: Uint32Array,
  float32: Float32Array
};

function decode(shapes) {
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

      } else if (attr === "shape") {
        if (type === "shapes") {
          if (obj.shape.ref === undefined) {
            obj.shape.vertices = convert(obj.shape.vertices);
            obj.shape.normals = convert(obj.shape.normals);
            obj.shape.edges = convert(obj.shape.edges);
            obj.shape.triangles = convert(obj.shape.triangles);
          } else {
            const ind = obj.shape.ref;
            if (ind !== undefined) {
              obj.shape = instances[ind];
            }
          }
        } else {
          obj.shape = convert(obj.shape);
        }
      }
    }
  }

  let instances = (shapes.instances == null) ? [] : shapes.instances
  instances.forEach((instance) => {
    instance.vertices = convert(instance.vertices);
    instance.normals = convert(instance.normals);
    instance.edges = convert(instance.edges);
    instance.triangles = convert(instance.triangles);
  });

  walk(shapes.shapes);
}

export { decode };
