We need answer only one JS code block, no extra text. Need craft robust deepEqual for Node.js plain function declaration no exports. Need satisfy spec carefully.

Need think through requirements:
- primitives compare with ===, except NaN equals NaN.
- Arrays equal same length and deep-equal elements; array never equals non-array.
- Plain objects equal same set own enumerable string keys and deep-equal values (key holding undefined different from missing key).
- Two Date equal when time values equal.
- Two Map equal when same keys (compared with ===) and deep-equal values.
- Two Set objects of primitives equal when contain same values.
- Objects of different kinds never equal, primitive never equals object.
- Cyclic structures must not cause infinite recursion: two structures with same shape of cycles are equal.

Need produce code block only. Need design implementation.

Need decide handling of other object kinds? Spec mentions plain objects, arrays, Date, Map, Set. What about functions? Objects of different kinds never equal. Could treat functions as objects? Need define kind. Plain objects likely objects whose prototype is Object.prototype or null? Need include. Other built-ins (RegExp, etc.) not specified; safest: only specified kinds equal; all other object kinds not equal unless same reference? Hmm primitives compare ===; objects? Usually deepEqual(a,a) true for same object? Spec doesn't explicitly say identical object references equal. It says objects of different kinds never equal. For same kind unspecified? Need infer. We can make same reference true early, which is reasonable and handles cycles. But if same reference to object with cycles, true. For different objects same shape cycles equal.

Need implement cycle detection. Common approach: track pairs of compared objects in a stack/set; if pair seen, return true. Need ensure same shape of cycles equal. Use a list of pairs (aObj,bObj) currently being compared; if encounter same pair again, return true. This handles cycles. Need also avoid false positives for repeated references? Example a = {x: obj, y: obj}, b = {x: obj1, y: obj2}; if obj deepEqual obj1 true and obj deepEqual obj2 true, fine. Pair tracking only ancestors, not all visited, so repeated sibling references re-compared (could exponential but okay). For cycles, ancestor pair returns true.

Need be careful with Map keys compared with ===. For Map equality: same keys (compared with ===) and deep-equal values. Need handle NaN as key? It says keys compared with ===, so NaN keys are not same? But primitives compare with === except NaN equals NaN earlier. For Map keys specifically compared with ===, so NaN !== NaN. Need follow literally: Map keys same compared with ===. But maybe SameValueZero? Spec says ===, so use strict equality. However if Map has NaN key, cannot match by ===; then maps with NaN keys would never equal even if same. That's per spec. But maybe they expect NaN equals NaN globally? It explicitly says Map keys compared with ===, so use ===. Need implement map key matching with strict equality. For values deep-equal. Need handle cycles involving Map values? Pair tracking works.

Set objects of primitives equal when contain same values. Need compare sets of primitives. What about NaN in Set? Set uses SameValueZero, so NaN equals NaN in Set. Spec says Set objects of primitives equal when contain same values. For primitives, NaN equals NaN per general rule? It says primitives compare with === except NaN equals NaN. Set contains same values likely SameValueZero semantics; NaN should equal NaN. Need implement set equality for primitives: same size and every value in a has matching value in b using primitive equality (NaN equal NaN). Since primitives only, can use SameValueZero-ish. Need handle -0 and +0? Set treats -0 and +0 same (SameValueZero). Primitive === treats -0 === +0 true too. NaN special. So use same primitiveEqual. For Set of objects? Spec says Set objects of primitives; if sets contain objects, maybe not equal unless same reference? It says two Set objects of primitives are equal when contain same values. It doesn't define object sets. Could either return false for non-primitive set elements or handle by reference? Need decide. "Two Set objects of primitives are equal when they contain the same values." Implies only primitive sets need support; object sets can be false (or maybe deep equality?). Safer: if any element not primitive, return false? But same reference sets? Hmm.

Need define primitive: null? typeof null is object but primitive. Need treat null as primitive. Primitives: undefined, null, boolean, number, string, bigint, symbol. Compare with === except NaN. Symbols: === works. BigInt === works.

Plain objects: own enumerable string keys. Need exclude symbols. Use Object.keys (string keys enumerable own). Need compare key sets exactly. Key holding undefined different from missing key: Object.keys includes keys with undefined values, so fine. Need compare values with deepEqual. Need ensure plain object definition: object whose prototype is Object.prototype or null? What about objects created with Object.create(null): plain? likely yes. What about class instances? Not plain, never equal? Spec only plain objects; objects of different kinds never equal. Need classify.

Need kind detection:
- if a === b return true (handles same reference and primitives too but primitives handled). But for NaN, a===b false; handle.
- if primitive either: return primitiveEqual(a,b) (which handles NaN). Actually if one primitive one object false.
- if Array.isArray both: compare length/elements. If one array other not false.
- Date both: getTime equal (NaN time? Date invalid time NaN; two invalid dates? getTime NaN; NaN equals NaN? Spec says Date equal when time values equal. Time values can be NaN; are NaN time values equal? It doesn't explicitly except NaN equals NaN for primitives. Date time values are numbers; "Two Date objects are equal when their time values are equal." If time values are NaN, are they equal? Could use Object.is? Hmm. Need decide. It says primitives compare with === except NaN equals NaN. Date time values are numbers but not primitives comparison? "when their time values are equal" likely use ===? Invalid dates both NaN; NaN not === NaN, but general NaN equals NaN might imply invalid dates equal? Ambiguous. Many deepEqual implementations use a.getTime() === b.getTime() || (isNaN both). Since NaN equals NaN rule maybe apply to time values too. I'd make invalid dates equal (NaN time equals NaN) to be consistent with NaN equals NaN. But spec specifically Date time values equal; NaN is not equal to NaN under ===. However earlier "primitives compare with ===, except that NaN equals NaN" only primitives, Date time values are primitives (numbers) when extracted? Could interpret. Need choose. Tests may check invalid dates? Possibly. Use same primitiveEqual for time values? That makes NaN equal NaN. Good.
- Map both: compare size and keys. Need match keys with === (not NaN). For each key in a, find matching key in b using ===; if found, deepEqual values. Need avoid using a key twice? If duplicate keys impossible in Map. Need ensure one-to-one? Since Map keys unique and same size, if every a key has a b key with === and values deep-equal, and sizes equal, then sets of keys same? Need consider a has keys 1 and '1', b has 1 and '1' fine. If a key matches multiple b keys? === is equivalence for primitives? For object keys, === identity; unique. For primitives, === equivalence except NaN (not equal). So matching is unique enough. But if a has NaN key, no b key matches via ===, so false. Good. Need not mark used because keys unique and equality transitive for === (except NaN not equal). For object keys identity unique. Fine.
- Set both: only primitives. Compare size and every element in a has matching element in b using primitiveEqual (NaN equal NaN, -0/+0 equal). Need handle duplicates impossible. If non-primitive element, maybe return false unless same reference? Spec only primitives; to be safe, if any element is object, return false? But same reference set? Hmm. Could support object elements by reference? Not specified; better not deep-equal objects in Set because Set equality for objects would require deep equality and cycle handling maybe possible but spec restricts to primitives. If sets contain objects, they are not "Set objects of primitives", so equality not defined; returning false is acceptable? But maybe tests expect deep equality for object sets? Unlikely. Need maybe implement general set equality using deepEqual for elements? But spec says Set objects of primitives; adding deep equality for objects could make object sets equal, not prohibited? It says two Set objects of primitives are equal when contain same values. It doesn't say object sets never equal. But "Objects of different kinds are never equal" only kinds. Could implement Set equality generally with deepEqual matching, but then need handle cycles and matching complexity. For primitives, deepEqual works. For objects, deepEqual matching could be expensive and ambiguous (which object matches which). Better restrict to primitives as spec: if any element not primitive, return false (except same reference? no). But if both sets are same reference, early a===b true. If different sets with same object references? Not primitives, false. Fine.
- Plain objects both: compare prototypes? Need define plain object: (proto === Object.prototype || proto === null). Also maybe objects with prototype Object.prototype but created via class? no. Need compare own enumerable string keys via Object.keys. Need ensure key holding undefined vs missing: Object.keys includes undefined-valued keys. Compare lengths and every key in a has own property in b and deepEqual values. Since same set of keys, check b has key via Object.prototype.hasOwnProperty.call(b,key) or Object.keys includes. Use hasOwn. Need compare values.
- Other object kinds: return false. But what about same reference early true. What about functions? If both functions same reference true; different functions false. Good.
- What about RegExp? different kinds false. Same reference true.
- What about typed arrays? Not specified; false unless same ref. Good.

Cycle handling: Need implement with a `pairs` array of [a,b] ancestors. At top of deepEqual, if both objects (non-primitive), check if pair already in pairs; if so return true. Then push pair, compute, pop. Need ensure for arrays/maps/sets/plain objects. For primitives no need. Implementation structure:

function deepEqual(a, b) {
  return deepEqualInternal(a, b, []);
}
But user asked write a JavaScript function `deepEqual(a, b)` as plain function declaration. Can include helper functions? They said reply with one code block; can include helper function declarations? Probably okay but maybe they want only function deepEqual. Better implement everything inside deepEqual using nested helper functions or default parameter? Plain function declaration no exports. We can define `function deepEqual(a, b) { ... }` with inner helpers. That's one function declaration plus inner functions. Acceptable. Or use a stack parameter via inner recursive function. Need not export.

Need be careful not to use `arguments`? fine.

Potential issue with pair tracking and Map/Set: If we push pair before comparing Map keys/values, cycles through Map values return true. Good.

Need implement `isPrimitive(value)`: value === null || (typeof value !== 'object' && typeof value !== 'function')? Functions are objects? For primitive check, functions are not primitives. Symbols/bigints typeof not object. Use `value === null || (typeof value !== 'object' && typeof value !== 'function')`. But what about `typeof` for undefined etc. Good.

`primitiveEqual(x,y)`: if (typeof x === 'number' && typeof y === 'number' && Number.isNaN(x) && Number.isNaN(y)) return true; return x === y;` Need also NaN for bigint? no. `Object.is` could handle NaN and -0 but -0 === +0 true; Object.is(-0,+0) false. Spec primitives === except NaN, so -0 === +0 true. Use custom.

`getKind(value)`:
- if Array.isArray(value) return 'array'
- if value instanceof Date return 'date' (but cross-realm? Node same realm; okay. Could use Object.prototype.toString.call? For Date, `value instanceof Date` fine. Need invalid Date still instanceof.)
- if value instanceof Map return 'map'
- if value instanceof Set return 'set'
- if isPlainObject(value) return 'object'
- else return 'other'
Need ensure `instanceof` with objects from different realms? Node not issue. Could use `Object.prototype.toString.call(value)` for robustness: '[object Date]', '[object Map]', '[object Set]', '[object Array]'. But Array.isArray better. For plain object, toString '[object Object]' includes class instances? Actually class instance toString is '[object Object]' unless Symbol.toStringTag. So need prototype check for plain. Use proto.

`isPlainObject(value)`: if value === null or typeof value !== 'object' return false; const proto = Object.getPrototypeOf(value); return proto === Object.prototype || proto === null;` What about objects with prototype `Object.prototype` but also `Symbol.toStringTag`? still plain? own enumerable string keys only; fine. What about `Object.create(null)` proto null plain. Good.

Need compare arrays: if kinds differ false. For arrays: length; loop i; if !deepEqualInternal(a[i], b[i], pairs) false. Note holes in arrays: own enumerable? Arrays can have holes; spec says arrays equal when same length and deep-equal elements. If one array has hole and other has undefined at same index, are elements deep-equal? `a[i]` yields undefined for hole, so would be equal to undefined element. But arrays with holes vs undefined elements: same length and elements? Spec doesn't mention holes; using a[i] treats hole as undefined. Should we distinguish holes? It says arrays equal when same length and deep-equal elements; a hole is not an element? Hmm. Own enumerable string keys for plain objects; arrays are not plain objects. For arrays, "same length and deep-equal elements" could imply holes? In JS, `[,]` length 1, `[undefined]` length 1; elements? `[,][0]` is undefined. Many deepEqual treat them equal. But if strict own keys, arrays have different keys ('0' missing vs present). Spec doesn't require distinguishing holes. Keep simple: compare length and indexed values. Could optionally compare holes via hasOwn to be precise? "Arrays are equal when they have the same length and deep-equal elements" — a hole means no element at index, so not deep-equal element? Ambiguous. Most tests won't use holes. But maybe should handle holes as different? Let's think.

The spec for plain objects explicitly says key holding undefined different from missing key. For arrays, not specified. It might be expected that arrays are compared by length and elements via indices; holes vs undefined maybe not tested. If we want robust, we could compare array own enumerable string keys too? But arrays can have extra own enumerable string keys (e.g., arr.foo=1). Spec doesn't say arrays with extra props equal? It says arrays equal when same length and deep-equal elements; doesn't mention extra properties. Should array with extra property equal array without? Probably not? Hmm.

Need decide scope. The rules are precise for plain objects but arrays only length/elements. It doesn't say arrays ignore extra own enumerable string keys. In JS, arrays are objects; but rule says arrays equal when same length and deep-equal elements. Could imply only length and elements matter, extra props ignored? Or arrays are a kind and extra props not considered? Usually deepEqual for arrays compares length and elements, not extra props. We'll follow: arrays compare length and indexed elements only. Holes: indexed access yields undefined; not distinguish. Fine.

Map comparison details:
```
if (a.size !== b.size) return false;
for (const [key, value] of a) {
  let found = false;
  for (const [bKey, bValue] of b) {
    if (key === bKey) { // strict, NaN false
      if (!deepEqualInternal(value, bValue, pairs)) return false;
      found = true;
      break;
    }
  }
  if (!found) return false;
}
return true;
```
Need ensure if a has key NaN, key === bKey false for all, found false -> false. Good. But what if b has NaN key and a has NaN key; false. Per spec.
Potential issue: Map keys can be objects; using === identity. If a and b are different maps with same object key references? e.g., const k={}; a=new Map([[k,1]]); b=new Map([[k,1]]); key===bKey true (same reference), values deepEqual -> true. Good. If different object keys with deep-equal contents, not same keys (===), false. Per spec.
Need avoid matching same b key multiple times? Map keys unique; a keys unique; if a has two different keys that are ===? impossible except? For primitives, 1 and 1 same key cannot duplicate. For objects, identity unique. So no need used set. But consider a has keys `1` and `'1'`, b has `1` and `'1'`; fine. a key `1` matches b key `1`; a key `'1'` matches b `'1'`. Good.

Set comparison:
```
if (a.size !== b.size) return false;
for (const value of a) {
  if (!isPrimitive(value)) return false; // or handle?
  let found=false;
  for (const bValue of b) {
    if (primitiveEqual(value,bValue)) { found=true; break; }
  }
  if (!found) return false;
}
return true;
```
Need ensure b values primitives too; if a primitive and b object, primitiveEqual false. If a non-primitive, return false. But what if both sets contain same object reference? Not primitives; spec doesn't require. Could maybe return true if same reference? But different Set objects with same object reference element: `new Set([obj])` vs `new Set([obj])`; are they equal? Not "Set objects of primitives". Could be considered not equal. Fine.
Need handle NaN in Set: primitiveEqual true. -0/+0 true. Good.
Potential issue: Set can contain `undefined`; primitiveEqual(undefined, undefined) true. Good.

Plain object comparison:
```
const aKeys = Object.keys(a); const bKeys = Object.keys(b);
if (aKeys.length !== bKeys.length) return false;
for (const key of aKeys) {
  if (!Object.prototype.hasOwnProperty.call(b, key)) return false;
  if (!deepEqualInternal(a[key], b[key], pairs)) return false;
}
return true;
```
Need ensure b has same set; length equal + every a key in b implies same set (since string keys unique). Good. Key holding undefined vs missing: hasOwnProperty distinguishes. Good.
Need compare own enumerable string keys only; Object.keys does that. Symbols ignored. Good.

Cycle pair tracking implementation:
```
function deepEqual(a, b) {
  const pairs = [];
  function isPrimitive(v) { ... }
  function primitiveEqual(x,y) { ... }
  function isPlainObject(v) { ... }
  function kindOf(v) { ... }
  function seen(aObj,bObj) { for (const [x,y] of pairs) if (x===aObj && y===bObj) return true; return false; }
  function eq(x,y) {
    if (primitiveEqual? no, need handle one primitive) ...
    if (isPrimitive(x) || isPrimitive(y)) {
      return isPrimitive(x) && isPrimitive(y) && primitiveEqual(x,y);
    }
    // both objects (or functions)
    if (x === y) return true;
    if (seen(x,y)) return true;
    const ka = kindOf(x), kb = kindOf(y);
    if (ka !== kb) return false;
    pairs.push([x,y]);
    let result;
    switch (ka) { ... }
    pairs.pop();
    return result;
  }
  return eq(a,b);
}
```
Need handle functions: isPrimitive false for functions; kindOf returns 'other' for functions; if x===y true; else ka===kb 'other' and then? Need not compare other kinds; return false. But if both functions different, false. If both other objects same kind but not specified, false. Need ensure for 'other' we don't push? We can push then return false; fine. But for same reference handled before. For different RegExp objects, kindOf both 'other', result false. Good.
Need for Date: kindOf 'date'; compare primitiveEqual(x.getTime(), y.getTime())? Use `const tx=x.getTime(), ty=y.getTime(); result = (tx === ty) || (Number.isNaN(tx) && Number.isNaN(ty));` Or primitiveEqual(tx,ty). Use primitiveEqual.
Need for Map/Set/Array/Object as above.
Need ensure `pairs.pop()` in finally to avoid leaking on exceptions? deepEqual shouldn't throw except maybe getters? Accessing a[key] can invoke getters and throw. If getter throws, pairs not popped but function exits via exception; no matter. Could use try/finally for cleanliness. Not necessary but can.
Need avoid infinite recursion in `seen`? no.
Need consider cyclic structures with same shape but different object identities: e.g., a={}; a.self=a; b={}; b.self=b; eq(a,b): both objects, not seen, kind object, push [a,b], compare keys self: eq(a,b) sees pair -> true. Good.
More complex: a={x:a,y:1}, b={x:b,y:1}; true. Different shape: a={x:a}, b={x:{}}; eq(a,b) push, key x eq(a,b) seen true -> would return true incorrectly? Wait b.x is a new object {}, not b. Let's construct: a = {}; a.x = a; b = {}; b.x = {}; (b.x is not b, it's a separate empty object). eq(a,b): push [a,b]; compare key x: eq(a, b.x). Pair [a,b] not same as [a,b.x]; b.x is object kind; push [a,b.x]; compare keys of a (x) and b.x (none): aKeys length 1 vs bKeys length 0 -> false. Good. If b.x = b (cycle to b), seen [a,b] true. Good.
Need same shape of cycles but different cycle targets: a.x = a; b.x = b; true. a.x = a.y? hmm.
Potential false positive with ancestor pair seen but structures not same? The standard algorithm returns true when encountering same pair again, which is correct for cycles: if we're already comparing a and b as ancestors, assuming they're equal is the coinductive interpretation. It handles cycles. Good.

Need think about Map cycles: a = new Map(); a.set('self', a); b = new Map(); b.set('self', b); eq(a,b): push [a,b]; compare values eq(a,b) seen true. Good.
Map with key object cycle? keys compared ===; if same key reference, fine. If different but deep-equal keys, false per spec. Good.

Need think about Set of primitives with cycles? no objects.

Need think about `Date` objects with same time but different kinds? both Date. Good.

Need think about `null`: isPrimitive true; primitiveEqual(null,null) true; null vs object false. Good.

Need think about `undefined`: same.

Need think about `NaN`: primitiveEqual true. `NaN` vs `undefined` false.

Need think about `Symbol`: primitiveEqual uses ===; symbols same reference true. `Symbol('x')` vs `Symbol('x')` false. Good.

Need think about `BigInt`: ===.

Need think about `-0` and `+0`: === true. Set uses primitiveEqual true. Good.

Need think about `Object.keys` on objects with getters that throw: not handle.

Need think about own enumerable string keys for plain objects with prototype null: Object.keys works. hasOwnProperty via Object.prototype.hasOwnProperty.call works even for null proto. Good.

Need think about `isPlainObject` for `Object.create(Object.prototype)` yes. For `new Object()` yes. For `Object.create(null)` yes. For `class Foo {}` instance proto Foo.prototype not plain -> other -> false unless same ref. Good. For `Object.create({})` proto {} not plain -> other. Good.

Need think about `Array` subclass instance: Array.isArray true, so treated as array even if subclass. Spec says arrays; okay. `new (class extends Array)` is array; compare length/elements. Fine.

Need think about `Map` subclass: instanceof Map true; treated as map. Fine.

Need think about cross-realm objects: instanceof may fail; not relevant Node. Could use `Object.prototype.toString` but then plain object detection still proto. For Date/Map/Set from another realm, instanceof false -> kind other -> false. Node single realm mostly. Could make robust with `Object.prototype.toString.call`: 
```
const tag = Object.prototype.toString.call(v);
if (tag === '[object Date]') ...
```
But `Object.prototype.toString.call` on object with null prototype? It works? `Object.prototype.toString.call(Object.create(null))` returns '[object Object]'? I think yes because toString is called with this=null-proto object; it uses internal slots, should return '[object Object]'. For arrays returns '[object Array]'. For Map/Set returns '[object Map]'/'[object Set]'. Could use both Array.isArray and toString for robustness. But toString can be fooled by Symbol.toStringTag for plain objects? e.g., `{ [Symbol.toStringTag]: 'Date' }` toString returns '[object Date]' but it's a plain object; if we use toString for kind, we'd misclassify as Date and then getTime not a function -> throw. So better use instanceof or internal slot checks. In Node, instanceof fine. For plain object with Symbol.toStringTag 'Date', isPlainObject true (proto Object.prototype) and kindOf should return object, not date. If kindOf uses toString first, bad. So use instanceof for Date/Map/Set after Array.isArray, then isPlainObject. A plain object with Symbol.toStringTag 'Map' still isPlainObject true; kindOf: not Array, not instanceof Map, not Date, not Set, isPlainObject true -> object. Good. A class instance with Symbol.toStringTag 'Map' but not instanceof Map -> other. Good.

Need think about `Date` with `Symbol.toStringTag`? instanceof Date true. Good.

Need think about `Map`/`Set` with null prototype? `Object.create(null)` not instanceof Map; isPlainObject true (proto null) -> object. Good.

Need think about `arguments` object: proto Object.prototype? In non-strict, arguments proto is Object.prototype? Actually `Object.getPrototypeOf(arguments) === Object.prototype` true? I think yes (or maybe `Object.prototype`). It would be treated as plain object and compare own enumerable string keys (indices and maybe callee in sloppy). Not specified; okay.

Need think about functions: `typeof function` is 'function', isPrimitive false, kindOf other. Same reference true; different false. Good.

Need think about `WeakMap`/`WeakSet`: other; false unless same ref. Good.

Need think about `Promise`: other. Good.

Need think about `Error`: other; false unless same ref. Good.

Need think about `RegExp`: other. Good.

Need think about `Buffer` (Uint8Array subclass): other; false unless same ref. Not specified. Good.

Need think about `TypedArray`: other. Good.

Need think about `ArrayBuffer`: other. Good.

Need think about `Boolean`/`Number`/`String` objects: typeof object, not plain? proto Boolean.prototype etc not Object.prototype/null -> other; false unless same ref. Spec primitives vs objects; boxed primitives are objects of different kind, never equal. Good.

Need think about `new String('a')` vs `'a'`: one object one primitive -> false. Good.

Need think about `Object.create(null)` with key '__proto__'? Object.keys includes; hasOwnProperty works; fine.

Need think about key holding undefined vs missing: covered.

Need think about enumerable string keys only: Object.keys excludes symbols and non-enumerable. Good.

Need think about `Map` values deep-equal with cycles: pairs includes [a,b] for maps; if value is a itself and b itself, seen true. Good.

Need think about `Set` primitives and `NaN`: primitiveEqual. Good.

Need think about `Set` with `-0` and `+0`: primitiveEqual true; Set itself treats them same. Good.

Need think about `Set` with `1` and `'1'`: primitiveEqual false; good.

Need think about `Map` keys `1` and `'1'`: strict false; good.

Need think about `Map` keys `NaN`: strict false; but maybe should NaN equal NaN? Spec explicitly ===. Good.

Need think about `Map` size same but keys match with === and values deep-equal; if a has key object k1 and b has key object k2 where k1===k2? same reference only. Good.

Need think about `Map` with same keys but values cyclic: pairs. Good.

Need think about performance: Map comparison O(n^2). Could optimize with a used set of b indices, but keys compared ===; for primitives could use Map from key to value? But keys can be objects; can use a Set of used b keys? For object keys, Set uses SameValueZero (NaN equal, -0/+0 same) not strict; not good for NaN (would match) and -0/+0 (same anyway). Could use array used flags. Simpler O(n^2) fine. But maybe for large maps, O(n^2) bad. Could implement better: since Map keys unique and equality is strict, we can build a `Set` of b keys? But Set uses SameValueZero, which would treat NaN as equal and -0/+0 as equal. For strict ===, -0/+0 are equal anyway (=== true), so only difference is NaN. If we use Set for b keys, NaN would be found, violating spec. Could special-case NaN: if typeof key === 'number' && Number.isNaN(key), no match. For other keys, Set membership uses SameValueZero; for -0/+0 same as ===; for all non-NaN primitives, SameValueZero equals ===? Let's check: SameValueZero: NaN equal NaN, +0/-0 equal, otherwise same as ===. For non-NaN, yes same as ===. For objects, SameValueZero is identity, same as ===. So we can use a Set of b keys for membership, but must exclude NaN keys (they never match). However we also need retrieve b value for matched key. We can build a Map from b key to b value? But Map keys use SameValueZero too; NaN keys would collide and -0/+0 same (okay). For non-NaN keys, Map get uses SameValueZero, same as ===. For object keys identity. So we could build `const bMap = new Map(b)`? But b is already a Map; we can iterate b and for each a key use `b.get(key)`? Wait Map.prototype.get uses SameValueZero, not strict. For non-NaN keys, same as ===. For NaN key, `b.get(NaN)` would return value if b has NaN key, but spec says keys compared with === so NaN should not match. So special-case NaN: if key is NaN, no match. For all other keys, `b.get(key)` works and returns value. But need ensure if b has NaN key and a has NaN key, we don't match; special-case. Also if a has -0 and b has +0, Map.get(-0) returns value for +0; === says -0 === +0 true, so okay. If a has NaN and b has NaN, special-case false. Good. This gives O(n). But need be careful: `b.get(key)` returns undefined if key not present, but if b has key with value undefined, `b.get(key)` returns undefined too; need use `b.has(key)` to distinguish. `b.has(key)` uses SameValueZero; for non-NaN same as ===. So:
```
if (typeof key === 'number' && Number.isNaN(key)) return false; // no strict match
if (!b.has(key)) return false;
if (!eq(value, b.get(key))) return false;
```
But what about a key that is `NaN` and b has a different NaN? false. Good. What about a key that is `-0`, b has `+0`: has true, get returns value; === true; good. What about a key that is `0` and b has `-0`: has true; === true; good. What about a key that is `NaN` but b has `NaN`: we return false; per spec. Good.
However, `b.has(key)` for key `NaN` would be true but we skip. Good.
This is O(n) and simpler. But need ensure if a has key `undefined`, b has key `undefined`: has true. Good. If a has key `null`, b has null: true. Good.
Potential issue: Map keys can be `NaN` and also `-0`; handled.
Need also ensure one-to-one matching? Since Map keys unique and sizes equal, if every a key has a matching b key (has) and values deep-equal, then the set of keys is same? Suppose a has keys 1 and 2; b has keys 1 and 1? impossible duplicate. b size 2 with keys 1 and 2. Fine. Suppose a has key 1, b has key 1 and also key NaN? sizes equal? a size 1, b size 2 no. If sizes equal and every a key in b, then b's keys are a superset? Since sizes equal and a keys unique, b must have exactly those keys? More formally, if a size = b size = n, and all n a keys are present in b (unique), then b contains at least n distinct keys, so exactly those n. Good. No need used flags.
But wait: `b.has(key)` for non-NaN uses SameValueZero; for key `-0`, b has `+0` true; that's same as ===. For key `NaN`, skip. For key `0`, b has `-0` true; === true. Good. For key `1` and b has `'1'`, has false. Good.
Need use `b.has` and `b.get`; but if b is a Map subclass with overridden has/get? instanceof Map but subclass could override has/get to throw or lie. Not worry. Could iterate b to avoid subclass overrides? Hmm. If subclass overrides `has`, our comparison could be fooled. Better not rely on Map methods? But we need compare maps; using `b.has`/`b.get` is natural. For robustness against malicious subclass, could iterate b entries and match with ===. But O(n^2). Spec doesn't mention malicious. Use iteration with === to strictly follow spec and avoid SameValueZero subtleties. Simpler and literal. O(n^2) acceptable. But maybe large maps in tests? Not likely. Could do O(n) with special-case NaN and still literal? It uses SameValueZero for non-NaN which equals ===, so okay. But to avoid any doubt, use iteration with ===. The spec explicitly says keys compared with ===; implementing with === is clearest. O(n^2) fine for typical. Let's use iteration with === to be literal. Need maybe optimize with a `used` array to ensure one-to-one? Not needed as argued. But if a has two keys that are ===? impossible. If a has key `NaN`, no match. Good.
Could use a `Set` of used b indices to be safe? Not needed. But consider a has keys `1` and `1`? impossible. Good.

Set comparison O(n^2) with primitiveEqual. Could use Set for b values but NaN handling; primitiveEqual handles NaN. O(n^2) fine. Could use a `Set` of b values and check a values; Set uses SameValueZero, which for primitives equals primitiveEqual (NaN equal, -0/+0 equal, otherwise ===). Actually primitiveEqual is exactly SameValueZero for primitives? SameValueZero: NaN equal NaN, +0/-0 equal, otherwise ===. Yes. So for primitive sets, we can use `new Set(b)` and check `bSet.has(value)`; but if value is object, Set has uses identity; we restrict primitives. For primitives, `bSet.has(value)` is correct. O(n). But need ensure b values are primitives; if a value primitive and b has object with same? Set.has(primitive) false. Good. If a has non-primitive, we return false before. So we can do:
```
if (a.size !== b.size) return false;
const bValues = new Set(b);
for (const value of a) {
  if (!isPrimitive(value)) return false;
  if (!bValues.has(value)) return false;
}
return true;
```
But `new Set(b)` uses SameValueZero; for primitives exactly primitiveEqual. Good. However if b contains non-primitive and a contains primitive, bValues.has(primitive) false; good. If a contains non-primitive, return false. This is O(n). But need be careful: if a contains non-primitive but b contains same reference, we return false; per spec (only primitives). Good.
Could also just iterate; simpler to reason. Use Set for efficiency? Maybe code clarity. I'll use iteration with primitiveEqual to avoid relying on Set semantics? But Set semantics are fine. Simpler code:
```
for (const value of a) {
  if (!isPrimitive(value)) return false;
  let found = false;
  for (const other of b) {
    if (primitiveEqual(value, other)) { found = true; break; }
  }
  if (!found) return false;
}
```
O(n^2). Fine.

Need think about `isPrimitive` for `function`: returns false. For `Set` of functions, return false. Good.

Need think about `primitiveEqual` for `undefined` and `null`: `x === y` true only same. Good.

Need think about `Number.isNaN` vs global isNaN: use Number.isNaN.

Need think about `Object.prototype.hasOwnProperty.call(b, key)`: if b is plain object with null proto, works. If b has own property `hasOwnProperty`? We call Object.prototype.hasOwnProperty, not b's, so safe. Good.

Need think about `Object.keys(a)` if a is plain object with null proto: works. Good.

Need think about `pairs` array and `seen`: use `for (const pair of pairs) { if (pair[0] === x && pair[1] === y) return true; }`. Good.

Need think about `eq` for both objects but one is array and other plain object: kindOf differs -> false. Good. Array vs non-array false. Date vs plain object false. Map vs Set false. Plain object vs Date false. Good.

Need think about `kindOf` for `null`: isPrimitive handles before, so kindOf not called on null. Good.

Need think about `eq` when one is primitive and other object: `isPrimitive(x) || isPrimitive(y)` true; return `isPrimitive(x) && isPrimitive(y) && primitiveEqual(x,y)`. If x primitive y object -> false. Good.

Need think about `x === y` for objects before kindOf: same reference true. For primitives, we already handled; but if both primitives and x===y, primitiveEqual would true anyway. We can do x===y after primitive check; for objects same ref true. Good.

Need think about `pairs.push` before switch and `pairs.pop` after. Use try/finally? If deepEqualInternal throws (getter), pairs not popped but exception propagates; no further use. Fine. But if we want clean, use try/finally. Code length okay.

Need think about `Date` invalid time: `primitiveEqual(x.getTime(), y.getTime())` returns true for NaN. Good. If we wanted strict ===, invalid dates false; but NaN equals NaN rule likely. Good.

Need think about `Map` with `NaN` keys and `Set` with `NaN`: Set uses primitiveEqual so NaN matches; Map uses === so NaN doesn't. This asymmetry is per spec. Good.

Need think about `Set` of primitives with `NaN` and `-0`: primitiveEqual true. Good.

Need think about `Set` size same but a has NaN and b has NaN: found true. Good.

Need think about `Set` with `undefined` and missing? Set has no missing. Good.

Need think about `Map` values `undefined` vs missing key: Map has key with undefined value vs no key; size differs or has false. Good.

Need think about `plain object` key with undefined vs missing: Object.keys includes undefined-valued key; length differs or hasOwn false. Good.

Need think about `plain object` with key `'constructor'` etc: Object.keys includes if own enumerable; hasOwnProperty works. Good.

Need think about `plain object` with non-enumerable key: ignored. Good.

Need think about `plain object` with symbol key: ignored. Good.

Need think about `plain object` with getter that returns different values on each access: could cause inconsistent; not handle.

Need think about `deepEqual` name collision: plain function declaration. Good.

Need produce exactly one code block and nothing else. Code block should contain only JS. No exports. Need not include tests.

Let's draft code:
```
function deepEqual(a, b) {
  const pairs = [];

  function isPrimitive(value) {
    return value === null || (typeof value !== 'object' && typeof value !== 'function');
  }

  function primitiveEqual(x, y) {
    return (typeof x === 'number' && typeof y === 'number' && Number.isNaN(x) && Number.isNaN(y)) || x === y;
  }

  function isPlainObject(value) {
    if (value === null || typeof value !== 'object') return false;
    const proto = Object.getPrototypeOf(value);
    return proto === Object.prototype || proto === null;
  }

  function kindOf(value) {
    if (Array.isArray(value)) return 'array';
    if (value instanceof Date) return 'date';
    if (value instanceof Map) return 'map';
    if (value instanceof Set) return 'set';
    if (isPlainObject(value)) return 'object';
    return 'other';
  }

  function alreadySeen(x, y) {
    for (const pair of pairs) {
      if (pair[0] === x && pair[1] === y) return true;
    }
    return false;
  }

  function eq(x, y) {
    if (isPrimitive(x) || isPrimitive(y)) {
      return isPrimitive(x) && isPrimitive(y) && primitiveEqual(x, y);
    }
    if (x === y) return true;
    if (alreadySeen(x, y)) return true;

    const kind = kindOf(x);
    if (kind !== kindOf(y)) return false;

    pairs.push([x, y]);
    let result = false;
    try {
      if (kind === 'array') {
        if (x.length !== y.length) {
          result = false;
        } else {
          result = true;
          for (let i = 0; i < x.length; i++) {
            if (!eq(x[i], y[i])) { result = false; break; }
          }
        }
      } else if (kind === 'date') {
        result = primitiveEqual(x.getTime(), y.getTime());
      } else if (kind === 'map') {
        if (x.size !== y.size) {
          result = false;
        } else {
          result = true;
          for (const [key, value] of x) {
            let found = false;
            for (const [otherKey, otherValue] of y) {
              if (key === otherKey) {
                if (!eq(value, otherValue)) { result = false; }
                found = true;
                break;
              }
            }
            if (!found) { result = false; break; }
            if (!result) break;
          }
        }
      } else if (kind === 'set') {
        if (x.size !== y.size) {
          result = false;
        } else {
          result = true;
          for (const value of x) {
            if (!isPrimitive(value)) { result = false; break; }
            let found = false;
            for (const other of y) {
              if (primitiveEqual(value, other)) { found = true; break; }
            }
            if (!found) { result = false; break; }
          }
        }
      } else if (kind === 'object') {
        const xKeys = Object.keys(x);
        const yKeys = Object.keys(y);
        if (xKeys.length !== yKeys.length) {
          result = false;
        } else {
          result = true;
          for (const key of xKeys) {
            if (!Object.prototype.hasOwnProperty.call(y, key) || !eq(x[key], y[key])) {
              result = false;
              break;
            }
          }
        }
      } else {
        result = false;
      }
    } finally {
      pairs.pop();
    }
    return result;
  }

  return eq(a, b);
}
```
Need check Map logic: Inside for x entries, if key matches otherKey, we set found=true and break; but if eq(value, otherValue) false, we set result=false but still found=true and break; then after inner loop, `if (!found)` false, then `if (!result) break;` breaks outer. Good. But if eq false, we set result=false and found=true; after inner loop, `if (!result) break;` yes. If eq true, result remains true; continue. Good. However if result was set false in a previous iteration, we break. Good.
But there's a subtle bug: In Map branch, if `x.size !== y.size`, result=false. Else result=true. In loop, if key matches and eq false, result=false; found=true; break inner; then `if (!found)` false; `if (!result) break;` good. If key doesn't match any, found=false; result=false; break. Good.
Need ensure if result becomes false inside inner eq, we don't continue to next x key. We break outer via `if (!result) break;`. Good.
Set branch: if value non-primitive, result=false break. If not found, false break. Good.
Object branch: if y missing key or eq false, result=false break. Good.
Array branch: if length mismatch false; else loop. Good.
Date branch: primitiveEqual. Good.
Other: false.
Need think about `pairs.pop()` in finally: if kind is 'other', we pushed pair then result=false; pop. Good. If x===y handled before push. If alreadySeen true before push. Good.
Need think about `alreadySeen` for objects that are same reference? handled before. Good.
Need think about `pairs` containing [x,y] and then `eq(x[i], y[i])` for array where x[i] is x itself and y[i] is y itself: alreadySeen true. Good.
Need think about `pairs` and `Map` where value is x itself and y itself: eq(x,y) alreadySeen true. Good.
Need think about `pairs` and `Set`: no object values allowed; if value non-primitive result false before recursion. Good.
Need think about `pairs` and `Date`: no recursion. Good.
Need think about `pairs` and `object` with key holding undefined: eq(