```javascript
function deepEqual(a, b) {
  const seen = new Map();

  function isPlainObject(obj) {
    if (obj === null || typeof obj !== 'object') return false;
    const proto = Object.getPrototypeOf(obj);
    return proto === Object.prototype || proto === null;
  }

  function eq(x, y) {
    if (typeof x === 'number' && typeof y === 'number' && Number.isNaN(x) && Number.isNaN(y)) {
      return true;
    }
    if (Object.is(x, y)) return true;

    if (typeof x !== 'object' || typeof y !== 'object' || x === null || y === null) {
      return false;
    }

    if (seen.has(x) && seen.get(x).has(y)) return true;
    if (!seen.has(x)) seen.set(x, new Set());
    seen.get(x).add(y);

    if (Array.isArray(x) || Array.isArray(y)) {
      if (!Array.isArray(x) || !Array.isArray(y)) return false;
      if (x.length !== y.length) return false;
      for (let i = 0; i < x.length; i++) {
        if (!eq(x[i], y[i])) return false;
      }
      return true;
    }

    if (x instanceof Date || y instanceof Date) {
      if (!(x instanceof Date) || !(y instanceof Date)) return false;
      return x.getTime() === y.getTime();
    }

    if (x instanceof Map || y instanceof Map) {
      if (!(x instanceof Map) || !(y instanceof Map)) return false;
      if (x.size !== y.size) return false;
      for (const [key, value] of x) {
        if (!y.has(key)) return false;
        if (!eq(value, y.get(key))) return false;
      }
      return true;
    }

    if (x instanceof Set || y instanceof Set) {
      if (!(x instanceof Set) || !(y instanceof Set)) return false;
      if (x.size !== y.size) return false;
      for (const value of x) {
        if (!y.has(value)) return false;
      }
      return true;
    }

    if (!isPlainObject(x) || !isPlainObject(y)) return false;

    const xKeys = Object.keys(x);
    const yKeys = Object.keys(y);
    if (xKeys.length !== yKeys.length) return false;
    for (const key of xKeys) {
      if (!Object.prototype.hasOwnProperty.call(y, key)) return false;
      if (!eq(x[key], y[key])) return false;
    }
    return true;
  }

  return eq(a, b);
}
```