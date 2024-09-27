"""Test the JupyterHub entry point"""

import asyncio
import binascii
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from subprocess import PIPE, Popen, check_output
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest.mock import patch

import pytest
import traitlets
from traitlets.config import Config

from jupyterhub.scopes import get_scopes_for

from .. import orm
from ..app import COOKIE_SECRET_BYTES, JupyterHub
from .mocking import MockHub
from .test_api import add_user


def test_help_all():
    out = check_output([sys.executable, '-m', 'jupyterhub', '--help-all']).decode(
        'utf8', 'replace'
    )
    assert '--ip' in out
    assert '--JupyterHub.ip' in out


@pytest.mark.skipif(traitlets.version_info < (5,), reason="requires traitlets 5")
def test_show_config(tmpdir):
    tmpdir.chdir()
    p = Popen(
        [sys.executable, '-m', 'jupyterhub', '--show-config', '--debug'], stdout=PIPE
    )
    p.wait(timeout=10)
    out = p.stdout.read().decode('utf8', 'replace')
    assert 'log_level' in out

    p = Popen(
        [sys.executable, '-m', 'jupyterhub', '--show-config-json', '--debug'],
        stdout=PIPE,
    )
    p.wait(timeout=10)
    out = p.stdout.read().decode('utf8', 'replace')
    config = json.loads(out)
    assert 'JupyterHub' in config
    assert config["JupyterHub"]["log_level"] == 10


def test_token_app():
    cmd = [sys.executable, '-m', 'jupyterhub', 'token']
    out = check_output(cmd + ['--help-all']).decode('utf8', 'replace')
    with TemporaryDirectory() as td:
        with open(os.path.join(td, 'jupyterhub_config.py'), 'w') as f:
            f.write("c.Authenticator.admin_users={'user'}")
        out = check_output(cmd + ['user'], cwd=td).decode('utf8', 'replace').strip()
    assert re.match(r'^[a-z0-9]+$', out)


def test_raise_error_on_missing_specified_config():
    """
    Using the -f or --config flag when starting JupyterHub should require the
    file to be found and exit if it isn't.
    """
    # subprocess.run doesn't have a timeout flag, so if this test would fail by
    # not letting jupyterhub error out, we would wait forever. subprocess.Popen
    # allow us to manually timeout.
    process = Popen(
        [sys.executable, '-m', 'jupyterhub', '--config', 'not-available.py']
    )
    # wait impatiently for the process to exit like we want it to
    for i in range(100):
        time.sleep(0.1)
        returncode = process.poll()
        if returncode is not None:
            break
    else:
        process.kill()
    assert returncode == 1


def test_generate_config():
    with NamedTemporaryFile(prefix='jupyterhub_config', suffix='.py') as tf:
        cfg_file = tf.name
    with open(cfg_file, 'w') as f:
        f.write("c.A = 5")
    p = Popen(
        [sys.executable, '-m', 'jupyterhub', '--generate-config', '-f', cfg_file],
        stdout=PIPE,
        stdin=PIPE,
    )
    out, _ = p.communicate(b'n')
    out = out.decode('utf8', 'replace')
    assert os.path.exists(cfg_file)
    with open(cfg_file) as f:
        cfg_text = f.read()
    assert cfg_text == 'c.A = 5'

    p = Popen(
        [sys.executable, '-m', 'jupyterhub', '--generate-config', '-f', cfg_file],
        stdout=PIPE,
        stdin=PIPE,
    )
    out, _ = p.communicate(b'x\ny')
    out = out.decode('utf8', 'replace')
    assert os.path.exists(cfg_file)
    with open(cfg_file) as f:
        cfg_text = f.read()
    os.remove(cfg_file)
    assert cfg_file in out
    assert 'Spawner.cmd' in cfg_text
    assert 'Authenticator.allowed_users' in cfg_text


async def test_init_tokens(request):
    with TemporaryDirectory() as td:
        db_file = os.path.join(td, 'jupyterhub.sqlite')
        tokens = {
            'super-secret-token': 'alyx',
            'also-super-secret': 'gordon',
            'boagasdfasdf': 'chell',
        }
        kwargs = {'db_url': db_file, 'api_tokens': tokens}
        ssl_enabled = getattr(request.module, "ssl_enabled", False)
        if ssl_enabled:
            kwargs['internal_certs_location'] = td
        app = MockHub(**kwargs)
        await app.initialize([])
        db = app.db
        for token, username in tokens.items():
            api_token = orm.APIToken.find(db, token)
            assert api_token is not None
            user = api_token.user
            assert user.name == username

        # simulate second startup, reloading same tokens:
        app = MockHub(**kwargs)
        await app.initialize([])
        db = app.db
        for token, username in tokens.items():
            api_token = orm.APIToken.find(db, token)
            assert api_token is not None
            user = api_token.user
            assert user.name == username

        # don't allow failed token insertion to create users:
        tokens['short'] = 'gman'
        app = MockHub(**kwargs)
        with pytest.raises(ValueError):
            await app.initialize([])
        assert orm.User.find(app.db, 'gman') is None


def test_write_cookie_secret(tmpdir, request):
    secret_path = str(tmpdir.join('cookie_secret'))
    kwargs = {'cookie_secret_file': secret_path}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)
    hub.init_secrets()
    assert os.path.exists(secret_path)
    assert os.stat(secret_path).st_mode & 0o600
    assert not os.stat(secret_path).st_mode & 0o177


def test_cookie_secret_permissions(tmpdir, request):
    secret_file = tmpdir.join('cookie_secret')
    secret_path = str(secret_file)
    secret = os.urandom(COOKIE_SECRET_BYTES)
    secret_file.write(binascii.b2a_hex(secret))
    kwargs = {'cookie_secret_file': secret_path}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)

    # raise with public secret file
    os.chmod(secret_path, 0o664)
    with pytest.raises(SystemExit):
        hub.init_secrets()

    # ok with same file, proper permissions
    os.chmod(secret_path, 0o660)
    hub.init_secrets()
    assert hub.cookie_secret == secret


def test_cookie_secret_content(tmpdir, request):
    secret_file = tmpdir.join('cookie_secret')
    secret_file.write('not base 64: uñiço∂e')
    secret_path = str(secret_file)
    os.chmod(secret_path, 0o660)
    kwargs = {'cookie_secret_file': secret_path}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)
    with pytest.raises(SystemExit):
        hub.init_secrets()


def test_cookie_secret_env(tmpdir, request):
    kwargs = {'cookie_secret_file': str(tmpdir.join('cookie_secret'))}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)

    with patch.dict(os.environ, {'JPY_COOKIE_SECRET': 'not hex'}):
        with pytest.raises(ValueError):
            hub.init_secrets()

    with patch.dict(os.environ, {'JPY_COOKIE_SECRET': 'abc123'}):
        hub.init_secrets()
    assert hub.cookie_secret == binascii.a2b_hex('abc123')
    assert not os.path.exists(hub.cookie_secret_file)


def test_cookie_secret_string():
    cfg = Config()

    cfg.JupyterHub.cookie_secret = "not hex"
    with pytest.raises(ValueError):
        JupyterHub(config=cfg)

    cfg.JupyterHub.cookie_secret = "abc123"
    app = JupyterHub(config=cfg)
    assert app.cookie_secret == binascii.a2b_hex('abc123')


async def test_load_groups(tmpdir, request):
    to_load = {
        'blue': {
            'users': ['cyclops', 'rogue', 'wolverine'],
        },
        'gold': {
            'users': ['storm', 'jean-grey', 'colossus'],
            'properties': {'setting3': 'three', 'setting4': 'four'},
        },
        'deprecated_list': ['jubilee', 'magik'],
    }
    kwargs = {'load_groups': to_load}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)
    hub.init_db()
    db = hub.db
    await hub.init_role_creation()
    await hub.init_users()
    await hub.init_groups()

    blue = orm.Group.find(db, name='blue')
    assert blue is not None
    assert sorted(u.name for u in blue.users) == sorted(to_load['blue']['users'])
    assert blue.properties == {}
    gold = orm.Group.find(db, name='gold')
    assert gold is not None
    assert sorted(u.name for u in gold.users) == sorted(to_load['gold']['users'])
    assert gold.properties == to_load['gold']['properties']
    deprecated_list = orm.Group.find(db, name='deprecated_list')
    assert deprecated_list is not None
    assert deprecated_list.properties == {}
    assert sorted(u.name for u in deprecated_list.users) == sorted(
        to_load['deprecated_list']
    )


@pytest.fixture
def persist_db(tmpdir):
    """ensure db will persist (overrides default sqlite://:memory:)"""
    if os.getenv('JUPYTERHUB_TEST_DB_URL'):
        # already using a db, no need
        yield
        return
    with patch.dict(
        os.environ,
        {'JUPYTERHUB_TEST_DB_URL': f"sqlite:///{tmpdir.join('jupyterhub.sqlite')}"},
    ):
        yield


@pytest.fixture
def new_hub(request, tmpdir, persist_db):
    """Fixture to launch a new hub for testing"""

    async def new_hub(**kwargs):
        ssl_enabled = getattr(request.module, "ssl_enabled", False)
        if ssl_enabled:
            kwargs['internal_certs_location'] = str(tmpdir)
        app = MockHub(test_clean_db=False, **kwargs)
        app.config.ConfigurableHTTPProxy.should_start = False
        app.config.ConfigurableHTTPProxy.auth_token = 'unused'
        request.addfinalizer(app.stop)
        await app.initialize([])

        return app

    return new_hub


async def test_resume_spawners(tmpdir, request, new_hub):
    app = await new_hub()
    db = app.db
    # spawn a user's server
    name = 'kurt'
    user = add_user(db, app, name=name)
    await user.spawn()
    proc = user.spawner.proc
    assert proc is not None

    # stop the Hub without cleaning up servers
    app.cleanup_servers = False
    app.stop()

    # proc is still running
    assert proc.poll() is None

    # resume Hub, should still be running
    app = await new_hub()
    db = app.db
    user = app.users[name]
    assert user.running
    assert user.spawner.server is not None

    # stop the Hub without cleaning up servers
    app.cleanup_servers = False
    app.stop()

    # stop the server while the Hub is down. BAMF!
    proc.terminate()
    proc.wait(timeout=10)
    assert proc.poll() is not None

    # resume Hub, should be stopped
    app = await new_hub()
    db = app.db
    user = app.users[name]
    assert not user.running
    assert user.spawner.server is None
    assert list(db.query(orm.Server)) == []


@pytest.mark.parametrize(
    'hub_config, expected',
    [
        ({'ip': '0.0.0.0'}, {'bind_url': 'http://0.0.0.0:8000/'}),
        (
            {'port': 123, 'base_url': '/prefix'},
            {'bind_url': 'http://:123/prefix/', 'base_url': '/prefix/'},
        ),
        ({'bind_url': 'http://0.0.0.0:12345/sub'}, {'base_url': '/sub/'}),
        (
            # no config, test defaults
            {},
            {'base_url': '/', 'bind_url': 'http://:8000', 'ip': '', 'port': 8000},
        ),
    ],
)
def test_url_config(hub_config, expected):
    # construct the config object
    cfg = Config()
    for key, value in hub_config.items():
        cfg.JupyterHub[key] = value

    # instantiate the Hub and load config
    app = JupyterHub(config=cfg)
    # validate config
    for key, value in hub_config.items():
        if key not in expected:
            assert getattr(app, key) == value

    # validate additional properties
    for key, value in expected.items():
        assert getattr(app, key) == value


@pytest.mark.parametrize(
    "base_url, hub_routespec, expected_routespec, should_warn, bad_prefix",
    [
        (None, None, "/", False, False),
        ("/", "/", "/", False, False),
        ("/base", "/base", "/base/", False, False),
        ("/", "/hub", "/hub/", True, False),
        (None, "hub/api", "/hub/api/", True, False),
        ("/base", "/hub/", "/hub/", True, True),
        (None, "/hub/api/health", "/hub/api/health/", True, True),
    ],
)
def test_hub_routespec(
    base_url, hub_routespec, expected_routespec, should_warn, bad_prefix, caplog
):
    cfg = Config()
    if base_url:
        cfg.JupyterHub.base_url = base_url
    if hub_routespec:
        cfg.JupyterHub.hub_routespec = hub_routespec
    with caplog.at_level(logging.WARNING):
        app = JupyterHub(config=cfg, log=logging.getLogger())
        app.init_hub()
    hub = app.hub
    assert hub.routespec == expected_routespec

    if should_warn:
        assert "custom route for Hub" in caplog.text
        assert hub_routespec in caplog.text
    else:
        assert "custom route for Hub" not in caplog.text

    if bad_prefix:
        assert "may not receive" in caplog.text
    else:
        assert "may not receive" not in caplog.text


@pytest.mark.parametrize(
    "argv, sys_argv",
    [
        (None, ["jupyterhub", "--debug", "--port=1234"]),
        (["--log-level=INFO"], ["jupyterhub"]),
    ],
)
def test_launch_instance(request, argv, sys_argv):
    class DummyHub(JupyterHub):
        def launch_instance_async(self, argv):
            # short-circuit initialize
            # by indicating we are going to generate config in start
            self.generate_config = True
            return super().launch_instance_async(argv)

        async def start(self):
            asyncio.get_running_loop().stop()

    DummyHub.clear_instance()
    request.addfinalizer(DummyHub.clear_instance)

    with patch.object(sys, "argv", sys_argv):
        DummyHub.launch_instance(argv)
    hub = DummyHub.instance()
    if argv is None:
        assert hub.argv == sys_argv[1:]
    else:
        assert hub.argv == argv


async def test_user_creation(tmpdir, request):
    allowed_users = {"in-allowed", "in-group-in-allowed", "in-role-in-allowed"}
    groups = {
        "group": {
            "users": ["in-group", "in-group-in-allowed"],
        }
    }
    roles = [
        {
            "name": "therole",
            "users": ["in-role", "in-role-in-allowed"],
        }
    ]

    cfg = Config()
    cfg.Authenticator.allow_all = False
    cfg.Authenticator.allowed_users = allowed_users
    cfg.JupyterHub.load_groups = groups
    cfg.JupyterHub.load_roles = roles
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    kwargs = dict(config=cfg)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)
    hub.init_db()

    await hub.init_role_creation()
    await hub.init_role_assignment()
    await hub.init_users()
    await hub.init_groups()
    assert hub.authenticator.allowed_users == {
        "admin",  # added by default config
        "in-allowed",
        "in-group-in-allowed",
        "in-role-in-allowed",
        "in-group",
        "in-role",
    }


async def test_recreate_service_from_database(
    request, new_hub, service_name, service_data
):
    # create a hub and add a service (not from config)
    app = await new_hub()
    app.service_from_spec(service_data, from_config=False)
    app.stop()

    # new hub, should load service from db
    app = await new_hub()
    assert service_name in app._service_map

    # verify keys
    service = app._service_map[service_name]
    for key, value in service_data.items():
        if key in {'api_token'}:
            # skip some keys
            continue
        assert getattr(service, key) == value

    assert (
        service_data['oauth_client_id'] in app.tornado_settings['oauth_no_confirm_list']
    )
    oauth_client = (
        app.db.query(orm.OAuthClient)
        .filter_by(identifier=service_data['oauth_client_id'])
        .first()
    )
    assert oauth_client.redirect_uri == service_data['oauth_redirect_uri']

    # delete service from db, start one more
    app.db.delete(service.orm)
    app.db.commit()

    # start one more, service should be gone
    app = await new_hub()
    assert service_name not in app._service_map


async def test_revoke_blocked_users(username, groupname, new_hub):
    config = Config()
    config.Authenticator.admin_users = {username}
    kept_username = username + "-kept"
    config.Authenticator.allowed_users = {username, kept_username}
    config.JupyterHub.load_groups = {
        groupname: {
            "users": [username],
        },
    }
    config.JupyterHub.load_roles = [
        {
            "name": "testrole",
            "scopes": ["access:services"],
            "groups": [groupname],
        }
    ]
    app = await new_hub(config=config)
    user = app.users[username]

    # load some credentials, start server
    await user.spawn()
    # await app.proxy.add_user(user)
    spawner = user.spawners['']
    token = user.new_api_token()
    orm_token = orm.APIToken.find(app.db, token)
    app.cleanup_servers = False
    app.stop()

    # before state
    assert await spawner.poll() is None
    assert sorted(role.name for role in user.roles) == ['admin', 'user']
    assert [g.name for g in user.groups] == [groupname]
    assert user.admin
    user_scopes = get_scopes_for(user)
    assert "access:servers" in user_scopes
    token_scopes = get_scopes_for(orm_token)
    assert "access:servers" in token_scopes

    # start a new hub, now with blocked users
    config = Config()
    name_doesnt_exist = user.name + "-doesntexist"
    config.Authenticator.blocked_users = {user.name, name_doesnt_exist}
    config.JupyterHub.init_spawners_timeout = 60
    # background spawner.proc.wait to avoid waiting for zombie process here
    with ThreadPoolExecutor(1) as pool:
        pool.submit(spawner.proc.wait)
        app2 = await new_hub(config=config)
    assert app2.db_url == app.db_url

    # check that blocked user has no permissions
    user2 = app2.users[user.name]
    assert user2.roles == []
    assert user2.groups == []
    assert user2.admin is False
    user_scopes = get_scopes_for(user2)
    assert user_scopes == set()
    orm_token = orm.APIToken.find(app2.db, token)
    token_scopes = get_scopes_for(orm_token)
    assert token_scopes == set()

    # spawner stopped
    assert user2.spawners == {}
    assert await spawner.poll() is not None

    # (sanity check) didn't lose other user
    kept_user = app2.users[kept_username]
    assert 'user' in [r.name for r in kept_user.roles]
    app2.stop()
