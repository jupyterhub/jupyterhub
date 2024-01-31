"""Utilities for memoization

Note: a memoized function should always return an _immutable_
result to avoid later modifications polluting cached results.
"""

from collections import OrderedDict
from functools import wraps


class DoNotCache:
    """Wrapper to return a result without caching it.

    In a function decorated with `@lru_cache_key`:

        return DoNotCache(result)

    is equivalent to:

        return result  # but don't cache it!
    """

    def __init__(self, result):
        self.result = result


class LRUCache:
    """A simple Least-Recently-Used (LRU) cache with a max size"""

    def __init__(self, maxsize=1024):
        self._cache = OrderedDict()
        self.maxsize = maxsize

    def __contains__(self, key):
        return key in self._cache

    def get(self, key, default=None):
        """Get an item from the cache"""
        if key in self._cache:
            # cache hit, bump to front of the queue for LRU
            result = self._cache[key]
            self._cache.move_to_end(key)
            return result
        return default

    def set(self, key, value):
        """Store an entry in the cache

        Purges oldest entry if cache is full
        """
        self._cache[key] = value
        # cache is full, purge oldest entry
        if len(self._cache) > self.maxsize:
            self._cache.popitem(last=False)

    __getitem__ = get
    __setitem__ = set


def lru_cache_key(key_func, maxsize=1024):
    """Like functools.lru_cache, but takes a custom key function,
    as seen in sorted(key=func).

    Useful for non-hashable arguments which have a known hashable equivalent (e.g. sets, lists),
    or mutable objects where only immutable fields might be used
    (e.g. User, where only username affects output).

    For safety: Cached results should always be immutable,
    such as using `frozenset` instead of mutable `set`.

    Example:

        @lru_cache_key(lambda user: user.name)
        def func_user(user):
            # output only varies by name

    Args:
        key (callable):
            Should have the same signature as the decorated function.
            Returns a hashable key to use in the cache
        maxsize (int):
            The maximum size of the cache.
    """

    def cache_func(func):
        cache = LRUCache(maxsize=maxsize)

        # the actual decorated function:
        @wraps(func)
        def cached(*args, **kwargs):
            cache_key = key_func(*args, **kwargs)
            if cache_key in cache:
                # cache hit
                return cache[cache_key]
            else:
                # cache miss, call function and cache result
                result = func(*args, **kwargs)
                if isinstance(result, DoNotCache):
                    # DoNotCache prevents caching
                    result = result.result
                else:
                    cache[cache_key] = result
            return result

        return cached

    return cache_func


class FrozenDict(dict):
    """A frozen dictionary subclass

    Immutable and hashable, so it can be used as a cache key

    Values will be frozen with `.freeze(value)`
    and must be hashable after freezing.

    Not rigorous, but enough for our purposes.
    """

    _hash = None

    def __init__(self, d):
        dict_set = dict.__setitem__
        for key, value in d.items():
            dict.__setitem__(self, key, self._freeze(value))

    def _freeze(self, item):
        """Make values of a dict hashable
        - list, set -> frozenset
        - dict -> recursive _FrozenDict
        - anything else: assumed hashable
        """
        if isinstance(item, FrozenDict):
            return item
        elif isinstance(item, list):
            return tuple(self._freeze(e) for e in item)
        elif isinstance(item, set):
            return frozenset(item)
        elif isinstance(item, dict):
            return FrozenDict(item)
        else:
            # any other type is assumed hashable
            return item

    def __setitem__(self, key):
        raise RuntimeError("Cannot modify frozen {type(self).__name__}")

    def update(self, other):
        raise RuntimeError("Cannot modify frozen {type(self).__name__}")

    def __hash__(self):
        """Cache hash because we are immutable"""
        if self._hash is None:
            self._hash = hash(tuple((key, value) for key, value in self.items()))
        return self._hash
