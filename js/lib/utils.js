// avoid loading lodash for "extend" function only
function extend(a, b) {
  Object.keys(b).forEach((key) => {
    a[key] = b[key];
  });
  return a;
}

function isThreeType(obj, type) {
  return (
    obj != null &&
    typeof obj === "object" &&
    obj.constructor != null &&
    obj.constructor.name === type
  );
}

function isTolEqual(obj1, obj2, tol = 1e-9) {
  // tolerant comparison

  // Convert three's Vector3 to arrays
  if (isThreeType(obj1, "Vector3")) {
    obj1 = obj1.toArray();
  }
  if (isThreeType(obj2, "Vector3")) {
    obj2 = obj2.toArray();
  }

  if (Array.isArray(obj1) && Array.isArray(obj2)) {
    return (
      obj1.length === obj2.length &&
      obj1.every((v, i) => isTolEqual(v, obj2[i]))
    );
  } else if (
    obj1 != null &&
    obj2 != null &&
    typeof obj1 === "object" &&
    typeof obj2 === "object"
  ) {
    var keys1 = Object.keys(obj1);
    var keys2 = Object.keys(obj2);

    if (
      keys1.length == keys2.length &&
      keys1.every((key) => Object.prototype.hasOwnProperty.call(obj2, key))
    ) {
      return keys1.every((key) => isTolEqual(obj1[key], obj2[key]));
    } else {
      return false;
    }
  } else {
    if (Number(obj1) === obj1 && Number(obj2) === obj2) {
      return Math.abs(obj1 - obj2) < tol;
    }
    return obj1 === obj2;
  }
}

export { extend, isThreeType, isTolEqual };
