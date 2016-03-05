from traitlets import HasTraits

from jupyterhub.traitlets import URLPrefix, Command

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

