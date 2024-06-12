import pytest

from kubespawner.slugs import is_valid_label, safe_slug


@pytest.mark.parametrize(
    "name, expected",
    [
        ("jupyter-alex", "jupyter-alex"),
        ("jupyter-Alex", "jupyter-alex---3a1c285c"),
        ("jupyter-üni", "jupyter-ni---a5aaf5dd"),
        ("endswith-", "endswith---165f1166"),
        ("user@email.com", "user-email-com---0925f997"),
        ("user-_@_emailß.com", "user-email-com---7e3a7efd"),
        ("has.dot", "has-dot---03e27fdf"),
        ("z9", "z9"),
        ("9z9", "x-9z9---224de202"),
        ("-start", "start---f587e2dc"),
        ("üser", "ser---73506260"),
        ("username--servername", "username-servername---d957f1de"),
        ("start---f587e2dc", "start-f587e2dc---cc5bb9c9"),
        pytest.param("x" * 63, "x" * 63, id="x63"),
        pytest.param("x" * 64, "xxxxxxxxxxxxxxxxxxxxx---7ce10097", id="x64"),
        pytest.param("x" * 65, "xxxxxxxxxxxxxxxxxxxxx---9537c5fd", id="x65"),
        ("", "x---e3b0c442"),
    ],
)
def test_safe_slug(name, expected):
    slug = safe_slug(name)
    assert slug == expected


@pytest.mark.parametrize(
    "max_length, length, expected",
    [
        (16, 16, "x" * 16),
        (16, 17, "xxxxx---d04fd59f"),
        (11, 16, "error"),
        (12, 16, "x---9c572959"),
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
        ("", ""),
        ("x", "x"),
        ("a-b", "a-b"),
        ("9a", "9a"),
        ("9.", "x-9---99a1b84b"),
        ("AbC", "AbC"),
        ("AbC.", "abc---dbe8c5d1"),
        ("ab.c", "ab.c"),
        ("a@b.c", "a-b-c---d648b243"),
        ("-x", "x---a4209624"),
        ("x-", "x---c8b60efc"),
        pytest.param("x" * 63, "x" * 63, id="x63"),
        pytest.param("x" * 64, "xxxxxxxxxxxxxxxxxxxxx---7ce10097", id="x64"),
        pytest.param("x" * 65, "xxxxxxxxxxxxxxxxxxxxx---9537c5fd", id="x65"),
    ],
)
def test_safe_slug_label(name, expected):
    slug = safe_slug(name, is_valid=is_valid_label)
    assert slug == expected
