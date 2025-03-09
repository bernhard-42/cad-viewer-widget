const MAP_HEX = {
  0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6,
  7: 7, 8: 8, 9: 9, a: 10, b: 11, c: 12, d: 13,
  e: 14, f: 15, A: 10, B: 11, C: 12, D: 13,
  E: 14, F: 15
};

function fromHex(hexString) {
  const bytes = new Uint8Array(Math.floor((hexString || "").length / 2));
  let i;
  for (i = 0; i < bytes.length; i++) {
      const a = MAP_HEX[hexString[i * 2]];
      const b = MAP_HEX[hexString[i * 2 + 1]];
      if (a === undefined || b === undefined) {
          break;
      }
      bytes[i] = (a << 4) | b;
  }
  return i === bytes.length ? bytes : bytes.slice(0, i);
}

function fromB64(s) {
  let bytes = atob(s);
  let uint = new Uint8Array(bytes.length);
  for (var i = 0; i < bytes.length; i++) uint[i] = bytes[i].charCodeAt(0);
  return uint;
}


function decode(data) {
  function convert(obj) {
      var result;
      if (typeof obj.buffer == "string") {
          var buffer;
          if (obj.codec === "b64") {
              buffer = fromB64(obj.buffer);
          } else {
              buffer = fromHex(obj.buffer);
          }
          if (obj.dtype === "float32") {
              result = new Float32Array(buffer.buffer);
          } else if (obj.dtype === "int32") {
              result = new Uint32Array(buffer.buffer);
          } else if (obj.dtype === "uint32") {
              result = new Uint32Array(buffer.buffer);
          } else {
              console.log("Error: unknown dtype", obj.dtype);
          }
      } else if (Array.isArray(obj)) {
          result = [];
          for (var arr of obj) {
              result.push(convert(arr));
          }
          return result;
      } else {
          console.log("Error: unknown buffer type", obj.buffer);
      }
      return result;
  }

  // function combineFloatArrays(input) {
  //     let totalLength = 0;
  //     for (let i = 0; i < input.length; i++) {
  //         totalLength += input[i].length;
  //     }
  //     let output = new Float32Array(totalLength);
  //     let offset = 0;
  //     for (let i = 0; i < input.length; i++) {
  //         output.set(input[i], offset);
  //         offset += input[i].length;
  //     }
  //     return output;
  // }

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
                      obj.shape.obj_vertices = convert(obj.shape.obj_vertices);
                      obj.shape.normals = convert(obj.shape.normals);
                      obj.shape.edge_types = convert(obj.shape.edge_types);
                      obj.shape.face_types = convert(obj.shape.face_types);
                      obj.shape.triangles = convert(obj.shape.triangles);
                      obj.shape.triangles_per_face = convert(obj.shape.triangles_per_face);
                      obj.shape.edges = convert(obj.shape.edges);
                      obj.shape.segments_per_edge = convert(obj.shape.segments_per_edge);
                  } else {
                      const ind = obj.shape.ref;
                      if (ind !== undefined) {
                          obj.shape = instances[ind];
                      }
                  }
              } else if (type === "edges") {
                  obj.shape.edges = convert(obj.shape.edges);
                  obj.shape.segments_per_edge = convert(obj.shape.segments_per_edge);
                  obj.shape.obj_vertices = convert(obj.shape.obj_vertices);
              } else {
                  obj.shape.obj_vertices = convert(obj.shape.obj_vertices);
              }
          }
      }
  }
  
  const instances = data.data.instances;

  data.data.instances.forEach((instance) => {
      instance.vertices = convert(instance.vertices);
      instance.obj_vertices = convert(instance.obj_vertices);
      instance.normals = convert(instance.normals);
      instance.edge_types = convert(instance.edge_types);
      instance.face_types = convert(instance.face_types);
      instance.triangles = convert(instance.triangles);
      instance.triangles_per_face = convert(instance.triangles_per_face);
      instance.edges = convert(instance.edges);
      instance.segments_per_edge = convert(instance.segments_per_edge);
  });

  walk(data.data.shapes);

  data.data.instances = []
}

export { decode };
