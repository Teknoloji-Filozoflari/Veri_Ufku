"""Parent-owned page LRU. Values are bounded display payloads, never DataFrames."""

import hashlib
import json
from collections import OrderedDict


def page_key(request, parameters):
    return hashlib.sha256(
        json.dumps(
            [request, parameters],
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
    ).hexdigest()


class PageCache:
    def __init__(self, pages=3, bytes_limit=64 * 1024**2):
        self.pages, self.bytes_limit = pages, bytes_limit
        self.entries = OrderedDict()
        self.bytes = 0

    def get(self, key):
        entry = self.entries.get(key)
        if entry:
            self.entries.move_to_end(key)
            return entry[0]

    def put(self, key, value):
        size = len(json.dumps(value, ensure_ascii=False).encode())
        if key in self.entries:
            self.bytes -= self.entries.pop(key)[1]
        if size > self.bytes_limit:
            return
        self.entries[key] = value, size
        self.bytes += size
        while len(self.entries) > self.pages or self.bytes > self.bytes_limit:
            self.bytes -= self.entries.popitem(last=False)[1][1]
