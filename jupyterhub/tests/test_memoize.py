import pytest

from jupyterhub._memoize import DoNotCache, FrozenDict, LRUCache, lru_cache_key


def test_lru_cache():
    cache = LRUCache(maxsize=2)
    cache["a"] = 1
    assert "a" in cache
    assert "b" not in cache
    cache["b"] = 2
    assert cache["b"] == 2

    # accessing a makes it more recent than b
    assert cache["a"] == 1
    assert "b" in cache
    assert "a" in cache

    # storing c pushes oldest ('b') out of cache
    cache["c"] = 3
    assert len(cache._cache) == 2
    assert "a" in cache
    assert "c" in cache
    assert "b" not in cache


def test_lru_cache_key():
    call_count = 0

    @lru_cache_key(frozenset)
    def reverse(arg):
        nonlocal call_count
        call_count += 1
        return list(reversed(arg))

    in1 = [1, 2]
    before = call_count
    out1 = reverse(in1)
    assert call_count == before + 1
    assert out1 == [2, 1]

    before = call_count
    out2 = reverse(in1)
    assert call_count == before
    assert out2 is out1


def test_do_not_cache():
    call_count = 0

    @lru_cache_key(lambda arg: arg)
    def is_even(arg):
        nonlocal call_count
        call_count += 1
        if arg % 2:
            return DoNotCache(False)
        return True

    before = call_count
    assert is_even(0) == True
    assert call_count == before + 1

    # caches even results
    before = call_count
    assert is_even(0) == True
    assert call_count == before

    before = call_count
    assert is_even(1) == False
    assert call_count == before + 1

    # doesn't cache odd results
    before = call_count
    assert is_even(1) == False
    assert call_count == before + 1


@pytest.mark.parametrize(
    "d",
    [
        {"key": "value"},
        {"key": ["list"]},
        {"key": {"set"}},
        {"key": ("tu", "ple")},
        {"key": {"nested": ["dict"]}},
    ],
)
def test_frozen_dict(d):
    frozen_1 = FrozenDict(d)
    frozen_2 = FrozenDict(d)
    assert hash(frozen_1) == hash(frozen_2)
    assert frozen_1 == frozen_2
