from .test_api import api_request, add_user

def test_create_named_server(app):
    return
    app.allow_named_servers = True
    username = 'user'
    servername = 'foo'
    r = api_request(app, 'users', username, 'servers', servername, method='post')
    r.raise_for_status()
    