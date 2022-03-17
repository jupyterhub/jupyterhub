"""Utilities for memoization"""
from collections import OrderedDict
from functools import wraps


class DoNotCache(Exception):
    """Special exception to return a result without caching it"""

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
                try:
                    result = func(*args, **kwargs)
                except DoNotCache as e:
                    # DoNotCache prevents caching
                    result = e.result
                else:
                    cache[cache_key] = result
            return result

        return cached

    return cache_func
