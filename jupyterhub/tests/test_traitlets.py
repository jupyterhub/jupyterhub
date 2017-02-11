"""Test traitlets"""
import pytest
from traitlets import HasTraits, TraitError

from jupyterhub.traitlets import URLPrefix, Command, ByteSpecification


def test_url_prefix():
    """Test url prefix configures correctly"""
    class C(HasTraits):
        """Test class for URLPrefix trait"""
        url = URLPrefix()
    c = C()
    c.url = '/a/b/c/'
    assert c.url == '/a/b/c/'
    c.url = '/a/b'
    assert c.url == '/a/b/'
    c.url = 'a/b/c/d'
    assert c.url == '/a/b/c/d/'


def test_command():
    """Test command trait"""
    class C(HasTraits):
        """Test class for Command trait"""
        cmd = Command('default command')
        cmd2 = Command(['default_cmd'])
    c = C()
    assert c.cmd == ['default command']
    assert c.cmd2 == ['default_cmd']
    c.cmd = 'foo bar'
    assert c.cmd == ['foo bar']


def test_memoryspec():
    """Test memory trait and converting string to numerical value"""
    class C(HasTraits):
        """Test class for ByteSpecification trait"""
        mem = ByteSpecification()

    c = C()

    c.mem = 1024
    assert c.mem == 1024

    c.mem = '1024K'
    assert c.mem == 1024 * 1024

    c.mem = '1024M'
    assert c.mem == 1024 * 1024 * 1024

    c.mem = '1024G'
    assert c.mem == 1024 * 1024 * 1024 * 1024

    c.mem = '1024T'
    assert c.mem == 1024 * 1024 * 1024 * 1024 * 1024

    with pytest.raises(TraitError):
        c.mem = '1024Gi'
