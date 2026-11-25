```python
import time
from collections import OrderedDict


class TTLCache:
    def __init__(self, capacity, ttl, clock=time.monotonic):
        self.capacity = capacity
        self.ttl = ttl
        self.clock = clock
        self._data = OrderedDict()  # key -> (value, timestamp)

    def _is_expired(self, timestamp):
        return self.clock() - timestamp >= self.ttl

    def _purge_expired(self):
        expired = [k for k, (_, ts) in self._data.items() if self._is_expired(ts)]
        for k in expired:
            del self._data[k]

    def put(self, key, value):
        now = self.clock()
        if key in self._data:
            self._data[key] = (value, now)
            self._data.move_to_end(key)
            return
        # New key: first drop expired entries, then evict LRU if still full.
        self._purge_expired()
        if len(self._data) >= self.capacity:
            self._data.popitem(last=False)
        self._data[key] = (value, now)

    def get(self, key):
        entry = self._data.get(key)
        if entry is None:
            return None
        value, ts = entry
        if self._is_expired(ts):
            del self._data[key]
            return None
        self._data.move_to_end(key)
        return value

    def __len__(self):
        self._purge_expired()
        return len(self._data)
```