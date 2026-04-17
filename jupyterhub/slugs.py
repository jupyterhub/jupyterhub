"""Tools for generating slugs like k8s object names and labels

Requirements:

- always valid for arbitary strings
- no collisions

# Design choices for safe_slug

This is originally based on
https://github.com/jupyterhub/kubespawner/blob/7.0.0/kubespawner/slugs.py
which creates slugs for final use, e.g. object names based on username+servername

safe_slug in this file is instead used for slugifying components.
Currently it's only used to handle servernames but in future JupyterHub or a
JupyterHub extension may use it for other components such as usernames.

In general safe_slug outputs a string that is URL and DNS safe
- Removes forbidden characters from input
- Appends a truncated hash of the input to distinguish inputs which look the same
  after forbidden characters are removed

Ideally we want to be able to safely combine two safe_slugs in a defined way,
e.g. if we guarantee slugs never contain '--' we can always use
{username-slug}--{servername-slug} with no risk of clashes.

If we forbid multiple consecutive `-` in the output of safe_slug we can handle
hyphens in the input by one of:
- a. allow `-`, always append hash
- b. allow `-`, conditionally append hash if input contains `-` or forbidden characters
- c. `-` is a disallowed character, always append hash
- d. `-` is a disallowed character, conditionally append hash if input contains
     forbidden characters

E.g. depending on the choice:
- `x-y` could end up as: `x-y-H1` or `xy-H1` where H1=HASH('x-y')
- `xy` could end up as: `xy` or `xy-H2` where H2=HASH('xy')

Note that if you require uniqueness between two different inputs, for example usernames,
you must always call safe_slug even if the input is "safe", as it's impossible to
distinguish between
- `input1-input2`
- safe_slug(`input1`) -> `input1-HASH` where `HASH` happens to equal `input2`

The approach currently taken in safe_slug is (b), which has the advantage of allowing
users to use `-` as a delimiter and still have it appear in the safe_slug.
Forbidden characters, consecutive `-` are replaced by `-`.

The default max length is 30 chars, so that two safe_slugs can be joined with `--`
and be within the limit for a domain name label (63 chars)
"""

import hashlib
import re
import string
import unicodedata

_alpha_lower = tuple(string.ascii_lowercase)
_alphanum_lower = tuple(string.ascii_lowercase + string.digits)

# patterns _do not_ need to cover length or start/end conditions,
# which are handled separately

_alphanum_pattern = re.compile(r'^[a-z0-9]+$')
# Allows `-` but not multiple consecutive `-`
_alphanum_hyphen_pattern = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

# match anything that's not lowercase alphanumeric (will be stripped, replaced with '-')
_non_alphanum_pattern = re.compile(r'[^a-z0-9]+')

# length of hash suffix
_hash_length = 8

# default max length of slug
_max_length = 30

# Unicode printable characters excluding whitespace, based on
# https://stackoverflow.com/questions/41757886/how-can-i-recognise-non-printable-unicode-characters-in-python/41761339#41761339
# https://www.fileformat.info/info/unicode/category/index.htm
printable_unicode_categories_excluding_whitespace = {
    # letters
    "LC",
    "Ll",
    "Lm",
    "Lo",
    "Lt",
    "Lu",
    # marks
    "Mc",
    "Me",
    "Mn",
    # numbers
    "Nd",
    "Nl",
    "No",
    # punctuation
    "Pc",
    "Pd",
    "Pe",
    "Pf",
    "Pi",
    "Po",
    "Ps",
    # symbol
    "Sc",
    "Sk",
    "Sm",
    "So",
}


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


def is_valid_safe_slug(s, max_length=_max_length):
    """Checks if this is a safe slug

    Requires:
    - 1-30 characters
    - starts with letter, ends with letter or digit
    - only lowercase ASCII letters, digits hyphen
    - multiple consecutive hyphens not allowed
    """
    return _is_valid_general(
        s,
        starts_with=_alpha_lower,
        ends_with=_alphanum_lower,
        pattern=_alphanum_hyphen_pattern,
        max_length=max_length,
        min_length=1,
    )


def is_valid_simple_name(s, max_length=_max_length):
    """is this potentially untrusted string valid as slug without modification?

    Requires:
    - 1-30 characters
    - starts with letter, ends with letter or digit
    - only lowercase ASCII letters and digits

    Hyphen `-` is not allowed here because we'll later use `-` as a substitute
    character and a delimiter
    """
    return _is_valid_general(
        s,
        starts_with=_alpha_lower,
        ends_with=_alphanum_lower,
        pattern=_alphanum_pattern,
        max_length=max_length,
        min_length=1,
    )


def _extract_safe_name(name, max_length):
    """Generate safe substring of a name

    Guarantees:

    - always starts with a lowercase letter
    - always ends with a lowercase letter or number
    - never more than one hyphen in a row (no '--')
    - only contains lowercase letters, numbers, '-'
    - length at least 1 ('x' if other rules strips down to empty string)
    - max length not exceeded
    """
    # compute safe slug from name (don't worry about collisions, hash handles that)
    # cast to lowercase
    # replace any sequence of non-alphanumeric characters with a single '-'
    safe_name = _non_alphanum_pattern.sub("-", name.lower())
    # truncate to max_length chars, strip '-' off ends
    safe_name = safe_name.lstrip("-")[:max_length].rstrip("-")
    # ensure starts with lowercase letter
    if safe_name and not safe_name.startswith(_alpha_lower):
        safe_name = "x-" + safe_name[: max_length - 1].rstrip("-")
    if not safe_name:
        # make sure it's non-empty
        safe_name = 'x'
    return safe_name


def strip_and_hash(name, max_length=_max_length):
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
    return f"{safe_name}-{name_hash}"


def safe_slug(name, is_valid=is_valid_simple_name, max_length=_max_length):
    """Always generate a safe slug for a non-empty string

    The returned slug will:
    - match regex [a-z0-9-]{1,max_length} (default max_length is 30)
    - be unique for a given input (within the probabilty of an 8 hex-digit hash collision)
    - no consecutive hypens (`--`)
    - starts with [a-z]
    - ends with [a-z0-9]
    - if the input matches [a-z][a-z0-9]{0,max_length-1} (i.e. only contains lowercase
      ASCII letters and digits, no hyphens, starts with a lowercase letter)
      it is returned unmodified
    - in all other cases it is modified to only contain [a-z0-9-] with no consecutive hyphens,
      and additionally is appended with a `-` and a 8 hex-digit hash

    This ensures that:
    - concatenating any number of safe_slugs with `--` will always be unique
    - concatenating two safe_slugs with `--` will be a valid DNS name
      (RFC 1035 and 1123: ASCII letters, digits, hyphens, max length 63)
    - it is always possible to tell whether a safe_slug required changing the input:
      if it was modified it will always end in `-HASH` where `HASH` is determined by
      JupyterHub, not the input e.g. `user-suffix` will become `user-suffix-HASH`
    """
    if not name:
        raise ValueError("Unable to create safe slug for empty string")
    if is_valid(name, max_length):
        return name
    return strip_and_hash(name, max_length)


def is_valid_display_name(s):
    """check display names are valid

    Between 1 and 255 chars
    Can contain most printable non whitespace unicode characters
    Can contain space (0x20)
    Must not start or end with space
    Must not contain multiple consecutive spaces
    """
    if len(s) < 1 or len(s) > 255:
        return False
    if "  " in s or s.startswith(" ") or s.endswith(" "):
        return False
    for c in s:
        if c == " ":
            continue
        if (
            unicodedata.category(c)
            not in printable_unicode_categories_excluding_whitespace
        ):
            return False
    return True


def normalise_unicode(s):
    return unicodedata.normalize("NFC", s)
