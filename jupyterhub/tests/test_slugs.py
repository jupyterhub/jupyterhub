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
    ],
)
def test_is_valid_simple_name(name, max_length, expected):
    if max_length:
        assert is_valid_simple_name(name, max_length) == expected
    else:
        assert is_valid_simple_name(name) == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("jupyter-alex", "jupyter-alex-651dec0a"),
        ("jupyter-Alex", "jupyter-alex-3a1c285c"),
        ("jupyter-üni", "jupyter-ni-a5aaf5dd"),
        ("endswith-", "endswith-165f1166"),
        ("user@email.com", "user-email-com-0925f997"),
        ("user-_@_emailß.com", "user-email-com-7e3a7efd"),
        ("has.dot", "has-dot-03e27fdf"),
        ("z9", "z9"),
        ("9z9", "x-9z9-224de202"),
        ("-start", "start-f587e2dc"),
        ("üser", "ser-73506260"),
        ("username-servername", "username-servername-9b109a32"),
        ("start-f587e2dc", "start-f587e2dc-06b9709d"),
        ("x" * 30, "x" * 30),
        ("x" * 31, "xxxxxxxxxxxxxxxxxxxxx-0f46e4b0"),
        ("x" * 32, "xxxxxxxxxxxxxxxxxxxxx-c62e4615"),
    ],
)
def test_safe_slug(name, expected):
    slug = safe_slug(name)
    assert slug == expected


@pytest.mark.parametrize(
    "max_length, length, expected",
    [
        (16, 16, "x" * 16),
        (16, 17, "xxxxxxx-d04fd59f"),
        (9, 10, "error"),
        (12, 16, "xxx-9c572959"),
        (30, 0, "error"),
    ],
)
def test_safe_slug_max_length(max_length, length, expected):
    name = "x" * length
    if expected == "error":
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
        ("🐧 🦆 🐣 🪿", True),
        ("∇²φ=0", True),
        ("x x", True),
        ("x  x", False),
        (" x", False),
        ("x ", False),
        ("x\tx", False),
        ("x\nx", False),
        ("", False),
        pytest.param("🐧" * 255, True, id="len255"),
        pytest.param("🐧" * 255, True, id="len256"),
    ],
)
def test_is_valid_display_name(name, expected):
    assert is_valid_display_name(name) == expected
