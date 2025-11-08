"""Tools for generating slugs like k8s object names and labels

Requirements:

- always valid for arbitary strings
- no collisions
"""

import hashlib
import re
import string

_alphanum = tuple(string.ascii_letters + string.digits)
_alpha_lower = tuple(string.ascii_lowercase)
_alphanum_lower = tuple(string.ascii_lowercase + string.digits)

# patterns _do not_ need to cover length or start/end conditions,
# which are handled separately
_object_pattern = re.compile(r'^[a-z0-9\-]+$')
_label_pattern = re.compile(r'^[a-z0-9\.\-_]+$', flags=re.IGNORECASE)

_alphanum_pattern = re.compile(r'^[a-z0-9]+$')

# match anything that's not lowercase alphanumeric (will be stripped, replaced with '-')
_non_alphanum_pattern = re.compile(r'[^a-z0-9]+')

# length of hash suffix
_hash_length = 8
# all hash suffixes should match this pattern
_hash_pattern = re.compile(rf'^[a-f0-9]{{{_hash_length}}}$')


def _is_valid_general(
    s, starts_with=None, ends_with=None, pattern=None, min_length=None, max_length=None
):
    """General is_valid check

    Checks rules:
    """
    if min_length and len(s) < min_length:
        return False
    if max_length and len(s) > max_length:
        return False
    if starts_with and not s.startswith(starts_with):
        return False
    if ends_with and not s.endswith(ends_with):
        return False
    if pattern and not pattern.match(s):
        return False
    return True


def is_valid_safe_slug(s):
    """Checks if this is a safe slug

    Either alphanumeric only, or a single '-' followed by a hash
    """
    if len(s) > 32:
        return False
    name, sep, suffix = s.partition("-")
    if not name or (sep and not suffix):
        return False
    if not _alphanum_pattern.match(name):
        return False
    if suffix and not _hash_pattern.match(suffix):
        return False
    return True


def is_valid_object_name(s):
    """is_valid check for object names

    Ensures all strictest object rules apply,
    satisfying both RFC 1035 and 1123 dns label name rules

    - 63 characters
    - starts with letter, ends with letter or number
    - only lowercalse letters, numbers, '-'
    """
    # object rules: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names
    return _is_valid_general(
        s,
        starts_with=_alpha_lower,
        ends_with=_alphanum_lower,
        pattern=_object_pattern,
        max_length=63,
        min_length=1,
    )


def is_valid_label(s):
    """is_valid check for label values"""
    # label rules: https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#syntax-and-character-set
    if not s:
        # empty strings are valid labels
        return True
    return _is_valid_general(
        s,
        starts_with=_alphanum,
        ends_with=_alphanum,
        pattern=_label_pattern,
        max_length=63,
    )


def is_valid_default(s):
    """Strict is_valid

    Returns True if it's valid for _all_ our known uses

    Currently, this is the same as is_valid_object_name,
    which produces a valid DNS label under RFC1035 AND RFC 1123,
    which is always also a valid label value.
    """
    return is_valid_object_name(s)


def _extract_safe_name(name, max_length):
    """Generate safe substring of a name

    Guarantees:

    - always starts with a lowercase letter
    - always ends with a lowercase letter or number
    - no hyphens (so clients are free to use hyphens for other purposes)
    - only contains lowercase letters, numbers
    - length at least 1 ('x' if other rules strips down to empty string)
    - max length not exceeded
    """
    # compute safe slug from name (don't worry about collisions, hash handles that)
    # cast to lowercase
    # replace all non-alphanumeric characters
    safe_name = _non_alphanum_pattern.sub("", name.lower())
    # truncate to max_length chars
    safe_name = safe_name[:max_length]
    # ensure starts with lowercase letter
    if safe_name and not safe_name.startswith(_alpha_lower):
        safe_name = "x" + safe_name[: max_length - 1]
    if not safe_name:
        # make sure it's non-empty
        safe_name = 'x'
    return safe_name


def strip_and_hash(name, max_length=32):
    """Generate an always-safe, unique string for any input

    truncates name to max_length - len(hash_suffix) to fit in max_length
    after adding hash suffix
    """
    name_length = max_length - (_hash_length + 1)
    if name_length < 1:
        raise ValueError(f"Cannot make safe names shorter than {_hash_length + 2}")
    # quick, short hash to avoid name collisions
    name_hash = hashlib.sha256(name.encode("utf8")).hexdigest()[:_hash_length]
    safe_name = _extract_safe_name(name, name_length)
    # the result will always have _exactly_ one '-'
    return f"{safe_name}-{name_hash}"


def safe_slug(name, is_valid=is_valid_default, max_length=32):
    """Always generate a safe slug

    is_valid should be a callable that returns True if a given string follows appropriate rules,
    and False if it does not.

    Given a string, if it's already valid, use it.
    If it's not valid, follow a safe encoding scheme that ensures:

    1. validity, and
    2. no collisions
    """
    if '-' in name:
        # don't accept any names that could collide with the safe slug
        return strip_and_hash(name, max_length=max_length)
    # allow max_length override for truncated sub-strings
    if is_valid(name) and (max_length is None or len(name) <= max_length):
        return name
    else:
        return strip_and_hash(name, max_length=max_length)


def multi_slug(names, max_length=48):
    """multi-component slug with single hash on the end

    same as strip_and_hash, but name components are joined with '--',
    so it looks like:

    {name1}--{name2}---{hash}

    In order to avoid hash collisions on boundaries, use `\\xFF` as delimiter
    """
    hasher = hashlib.sha256()
    hasher.update(names[0].encode("utf8"))
    for name in names[1:]:
        # \xFF can't occur as a start byte in UTF8
        # so use it as a word delimiter to make sure overlapping words don't collide
        hasher.update(b"\xff")
        hasher.update(name.encode("utf8"))
    hash = hasher.hexdigest()[:_hash_length]

    name_slugs = []
    available_chars = max_length - (_hash_length + 1)
    # allocate equal space per name
    # per_name accounts for '{name}--', so really two less
    per_name = available_chars // len(names)
    name_max_length = per_name - 2
    if name_max_length < 2:
        raise ValueError(f"Not enough characters for {len(names)} names: {max_length}")
    for name in names:
        name_slugs.append(_extract_safe_name(name, name_max_length))

    # by joining names with '--', this cannot collide with single-hashed names,
    # which can only contain '-' and the '---' hash delimiter once
    return f"{'--'.join(name_slugs)}---{hash}"
