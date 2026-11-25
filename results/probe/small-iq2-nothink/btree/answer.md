```python
import bisect


class BTreeNode:
    def __init__(self, leaf=True):
        self.keys = []
        self.children = []
        self.leaf = leaf


class BTree:
    def __init__(self, t):
        if not isinstance(t, int) or t < 2:
            raise ValueError("minimum degree t must be an integer >= 2")
        self.t = t
        self.root = BTreeNode(leaf=True)

    def __contains__(self, key):
        return self._search(self.root, key) is not None

    def keys(self):
        result = []
        self._collect_keys(self.root, result)
        return result

    def insert(self, key):
        if key in self:
            return
        root = self.root
        if len(root.keys) == 2 * self.t - 1:
            new_root = BTreeNode(leaf=False)
            new_root.children.append(root)
            self._split_child(new_root, 0)
            self.root = new_root
            self._insert_nonfull(new_root, key)
        else:
            self._insert_nonfull(root, key)

    def delete(self, key):
        if key not in self:
            return
        self._delete(self.root, key)
        if not self.root.keys and not self.root.leaf:
            self.root = self.root.children[0]

    # ---------- internal helpers ----------

    def _search(self, node, key):
        i = bisect.bisect_left(node.keys, key)
        if i < len(node.keys) and node.keys[i] == key:
            return (node, i)
        if node.leaf:
            return None
        return self._search(node.children[i], key)

    def _collect_keys(self, node, out):
        if node.leaf:
            out.extend(node.keys)
            return
        for i, k in enumerate(node.keys):
            self._collect_keys(node.children[i], out)
            out.append(k)
        self._collect_keys(node.children[-1], out)

    def _split_child(self, parent, i):
        t = self.t
        full = parent.children[i]
        new_node = BTreeNode(leaf=full.leaf)
        parent.keys.insert(i, full.keys[t - 1])
        parent.children.insert(i + 1, new_node)
        new_node.keys = full.keys[t:]
        full.keys = full.keys[:t - 1]
        if not full.leaf:
            new_node.children = full.children[t:]
            full.children = full.children[:t]

    def _insert_nonfull(self, node, key):
        t = self.t
        i = bisect.bisect_left(node.keys, key)
        if node.leaf:
            node.keys.insert(i, key)
            return
        child = node.children[i]
        if len(child.keys) == 2 * t - 1:
            self._split_child(node, i)
            if key > node.keys[i]:
                i += 1
        self._insert_nonfull(node.children[i], key)

    def _delete(self, node, key):
        t = self.t
        i = bisect.bisect_left(node.keys, key)
        if i < len(node.keys) and node.keys[i] == key:
            if node.leaf:
                node.keys.pop(i)
            else:
                self._delete_from_internal(node, i)
            return
        if node.leaf:
            return
        if len(node.children[i].keys) < t:
            self._fill_child(node, i)
            if i > len(node.keys):
                i -= 1
        self._delete(node.children[i], key)

    def _delete_from_internal(self, node, i):
        t = self.t
        key = node.keys[i]
        left = node.children[i]
        right = node.children[i + 1]
        if len(left.keys) >= t:
            pred = self._max_key(left)
            node.keys[i] = pred
            self._delete(left, pred)
        elif len(right.keys) >= t:
            succ = self._min_key(right)
            node.keys[i] = succ
            self._delete(right, succ)
        else:
            left.keys.append(key)
            left.keys.extend(right.keys)
            left.children.extend(right.children)
            node.keys.pop(i)
            node.children.pop(i + 1)
            self._delete(left, key)

    def _fill_child(self, node, i):
        t = self.t
        if i > 0 and len(node.children[i - 1].keys) >= t:
            self._borrow_from_prev(node, i)
        elif i < len(node.children) - 1 and len(node.children[i + 1].keys) >= t:
            self._borrow_from_next(node, i)
        else:
            if i < len(node.children) - 1:
                self._merge_children(node, i)
            else:
                self._merge_children(node, i - 1)

    def _borrow_from_prev(self, node, i):
        child = node.children[i]
        sibling = node.children[i - 1]
        child.keys.insert(0, node.keys[i - 1])
        node.keys[i - 1] = sibling.keys.pop()
        if not sibling.leaf:
            child.children.insert(0, sibling.children.pop())

    def _borrow_from_next(self, node, i):
        child = node.children[i]
        sibling = node.children[i + 1]
        child.keys.append(node.keys[i])
        node.keys[i] = sibling.keys.pop(0)
        if not sibling.leaf:
            child.children.append(sibling.children.pop(0))

    def _merge_children(self, node, i):
        left = node.children[i]
        right = node.children[i + 1]
        left.keys.append(node.keys.pop(i))
        left.keys.extend(right.keys)
        left.children.extend(right.children)
        node.children.pop(i + 1)

    def _max_key(self, node):
        while not node.leaf:
            node = node.children[-1]
        return node.keys[-1]

    def _min_key(self, node):
        while not node.leaf:
            node = node.children[0]
        return node.keys[0]
```