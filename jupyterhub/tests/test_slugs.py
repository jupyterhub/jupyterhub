import pytest

from ..slugs import (
    is_valid_display_name,
    is_valid_safe_slug,
    is_valid_simple_name,
    safe_slug,
)


@pytest.mark.parametrize(
    "name, max_length, expected",
    [
        ("a", None, True),
        ("a-1-2-3", None, True),
        ("jupyter-alex-651dec0a", None, True),
        ("1", None, False),
        ("a--1", None, False),
        ("-a", None, False),
        ("a-", None, False),
        ("üni", None, False),
        ("a" * 30, None, True),
        ("a" * 31, None, False),
        ("a" * 10, 10, True),
        ("a" * 11, 10, False),
    ],
)
def test_is_valid_safe_slug(name, max_length, expected):
    if max_length:
        assert is_valid_safe_slug(name, max_length) == expected
    else:
        assert is_valid_safe_slug(name) == expected


@pytest.mark.parametrize(
    "name, max_length, expected",
    [
        ("a", None, True),
        ("a1", None, True),
        ("1", None, False),
        ("a-1", None, False),
        ("-a", None, False),
        ("a-", None, False),
        ("üni", None, False),
        ("a" * 30, None, True),
        ("a" * 31, None, False),
        ("a" * 10, 10, True),
        ("a" * 11, 10, False),
    ],
)
def test_is_valid_simple_name(name, max_length, expected):
    if max_length:
        assert is_valid_simple_name(name, max_length) == expected
    else:
        assert is_valid_simple_name(name) == expected


@pytest.mark.parametrize(
    "name, expected_hash, expected_nohash",
    # Keep these in sync with share/jupyterhub/static/js/utils.test.js::utils.safe_slug
    [
        # Unchanged
        ["z9", "z9", "z9"],
        # Contains - so append hash
        ["jupyter-alex", "jupyter-alex-651dec0a", "jupyter-alex"],
        ["username-servername", "username-servername-9b109a32", "username-servername"],
        # Lowercase
        ["jupyter-Alex", "jupyter-alex-3a1c285c", "jupyter-alex"],
        # Invalid chars
        ["jupyter-üni", "jupyter-uni-a5aaf5dd", "jupyter-uni"],
        ["user@email.com", "user-email-com-0925f997", "user-email-com"],
        ["user-_@_emailß.com", "user-email-com-7e3a7efd", "user-email-com"],
        ["has.dot", "has-dot-03e27fdf", "has-dot"],
        ["üser-🐧½", "user-1-2-f3e0bac6", "user-1-2"],
        # Multiple -
        ["a-b--c-d", "a-b-c-d-ee1e7bc7", "a-b-c-d"],
        # Doesn't start with [a-z]
        ["9z9", "x-9z9-224de202", "x-9z9"],
        ["-start", "start-f587e2dc", "start"],
        # Ends with -
        ["endswith-", "endswith-165f1166", "endswith"],
        # Looks like it has a hash appended but that's irrelevant
        ["start-f587e2dc", "start-f587e2dc-06b9709d", "start-f587e2dc"],
        # Length tests
        ["x" * 30, "x" * 30, "x" * 30],
        ["x" * 31, "xxxxxxxxxxxxxxxxxxxxx-0f46e4b0", "x" * 30],
        ["x" * 32, "xxxxxxxxxxxxxxxxxxxxx-c62e4615", "x" * 30],
        # Length tests with invalid chars
        ["x" * 29 + "-", "xxxxxxxxxxxxxxxxxxxxx-bf57e3d7", "x" * 29],
        [
            "1234567890" * 3,
            "x-1234567890123456789-f54e5c8f",
            "x-1234567890123456789012345678",
        ],
    ],
)
def test_safe_slug(name, expected_hash, expected_nohash):
    slug_with_hash = safe_slug(name)
    assert expected_hash == slug_with_hash
    slug_without_hash = safe_slug(name, avoid_collisions=False)
    assert expected_nohash == slug_without_hash


@pytest.mark.parametrize(
    "max_length, length, expected",
    [
        (16, 16, "x" * 16),
        (16, 17, "xxxxxxx-d04fd59f"),
        (9, 10, "<ERROR>"),
        (12, 16, "xxx-9c572959"),
        (30, 0, "<ERROR>"),
    ],
)
def test_safe_slug_max_length(max_length, length, expected):
    name = "x" * length
    if expected == "<ERROR>":
        with pytest.raises(ValueError):
            safe_slug(name, max_length=max_length)
        return

    slug = safe_slug(name, max_length=max_length)
    assert slug == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("eèéêë", True),
        ("EÈÉÊË", True),
        ("北京大学", True),
        # Note we determine valid characters by checking the unicode category but
        # old Python versions class new unicode symbols as non-characters
        # E.g. 🪿 won't be accepted in Python 3.10
        ("🐧 🦆 🐣", True),
        ("∇²φ=0", True),
        ("x x", True),
        ("x  x", False),
        (" x", False),
        ("x ", False),
        ("x\tx", False),
        ("x\nx", False),
        ("", False),
        pytest.param("🐧" * 255, True, id="len255"),
        pytest.param("🐧" * 256, False, id="len256"),
    ],
)
def test_is_valid_display_name(name, expected):
    assert is_valid_display_name(name) == expected
