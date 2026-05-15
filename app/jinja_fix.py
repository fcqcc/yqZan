"""
Jinja2 LRU cache fix for Python 3.14 compatibility.

Python 3.14 dict raises TypeError for unhashable keys instead of KeyError.
This patches the internal _mapping dict with a safe version.
"""
import jinja2.utils
from collections import OrderedDict


class SafeDict(OrderedDict):
    """OrderedDict that handles unhashable keys gracefully."""
    def __contains__(self, key):
        try:
            return super().__contains__(key)
        except TypeError:
            return False

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except TypeError:
            raise KeyError(key)

    def __setitem__(self, key, value):
        try:
            super().__setitem__(key, value)
        except TypeError:
            pass

    def __delitem__(self, key):
        try:
            super().__delitem__(key)
        except TypeError:
            pass


orig_init = jinja2.utils.LRUCache.__init__

def safe_init(self, capacity):
    self.capacity = capacity
    self._mapping = SafeDict()
    from collections import deque
    from threading import Lock
    self._queue = deque()
    self._popleft = self._queue.popleft
    self._pop = self._queue.pop
    self._remove = self._queue.remove
    self._wlock = Lock()
    self._append = self._queue.append

jinja2.utils.LRUCache.__init__ = safe_init

print("✅ Jinja2 LRUCache patched for Python 3.14")
