import pytest
from traitlets import HasTraits, TraitError

from jupyterhub.traitlets import URLPrefix, Command, ByteSpecification


def test_url_prefix():
    class C(HasTraits):
        url = URLPrefix()
    c = C()
    c.url = '/a/b/c/'
    assert c.url == '/a/b/c/'
    c.url = '/a/b'
    assert c.url == '/a/b/'
    c.url = 'a/b/c/d'
    assert c.url == '/a/b/c/d/'


def test_command():
    class C(HasTraits):
        cmd = Command('default command')
        cmd2 = Command(['default_cmd'])
    c = C()
    assert c.cmd == ['default command']
    assert c.cmd2 == ['default_cmd']
    c.cmd = 'foo bar'
    assert c.cmd == ['foo bar']


def test_memoryspec():
    class C(HasTraits):
        mem = ByteSpecification()

    c = C()

    c.mem = 1024
    assert isinstance(c.mem, int)
    assert c.mem == 1024

    c.mem = '1024K'
    assert isinstance(c.mem, int)
    assert c.mem == 1024 * 1024

    c.mem = '1024M'
    assert isinstance(c.mem, int)
    assert c.mem == 1024 * 1024 * 1024

    c.mem = '1.5M'
    assert isinstance(c.mem, int)
    assert c.mem == 1.5 * 1024 * 1024

    c.mem = '1024G'
    assert isinstance(c.mem, int)
    assert c.mem == 1024 * 1024 * 1024 * 1024

    c.mem = '1024T'
    assert isinstance(c.mem, int)
    assert c.mem == 1024 * 1024 * 1024 * 1024 * 1024

    with pytest.raises(TraitError):
        c.mem = '1024Gi'
