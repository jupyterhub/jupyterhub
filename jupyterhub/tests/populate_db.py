"""script to populate a jupyterhub database

Run with old versions of jupyterhub to test upgrade/downgrade

used in test_db.py
"""

from datetime import datetime
from functools import partial

import jupyterhub
from jupyterhub import orm


def populate_db(url):
    """Populate a jupyterhub database"""
    connect_args = {}
    if 'mysql' in url:
        connect_args['auth_plugin'] = 'mysql_native_password'
    db = orm.new_session_factory(url, connect_args=connect_args)()

    if jupyterhub.version_info >= (2,):
        if (
            not db.query(orm.OAuthClient)
            .filter_by(identifier="jupyterhub")
            .one_or_none()
        ):
            # create the oauth client for jupyterhub itself
            # this allows us to distinguish between orphaned tokens
            # (failed cascade deletion) and tokens issued by the hub
            # it has no client_secret, which means it cannot be used
            # to make requests
            client = orm.OAuthClient(
                identifier="jupyterhub",
                secret="",
                redirect_uri="",
                description="JupyterHub",
            )
            db.add(client)
            db.commit()

        from jupyterhub import roles

        for role in roles.get_default_roles():
            roles.create_role(db, role)

    # create some users
    admin = orm.User(name='admin', admin=True)
    db.add(admin)
    user = orm.User(name='has-server')
    db.add(user)
    db.commit()

    # create a group
    g = orm.Group(name='group')
    db.add(g)
    db.commit()
    g.users.append(user)
    db.commit()

    service = orm.Service(name='service')
    db.add(service)
    db.commit()

    # create some API tokens
    user.new_api_token()
    admin.new_api_token()

    # services got API tokens in 0.7
    if jupyterhub.version_info >= (0, 7):
        # create a group
        service.new_api_token()

    # Create a Spawner for user
    if jupyterhub.version_info >= (0, 8):
        # create spawner for user
        spawner = orm.Spawner(name='', user=user)
        db.add(spawner)
        db.commit()
        spawner.server = orm.Server()
        db.commit()

        # admin's spawner is not running
        spawner = orm.Spawner(name='', user=admin)
        db.add(spawner)
        db.commit()
    else:
        user.server = orm.Server()
        db.commit()

    # create some oauth objects
    client = orm.OAuthClient(identifier='oauth-client')
    db.add(client)
    db.commit()
    code = orm.OAuthCode(client_id=client.identifier)
    db.add(code)
    db.commit()
    if jupyterhub.version_info < (2, 0):
        Token = partial(
            orm.OAuthAccessToken,
            grant_type=orm.GrantType.authorization_code,
        )
    else:
        Token = orm.APIToken
    access_token = Token(
        client_id=client.identifier,
        user_id=user.id,
    )
    if jupyterhub.version_info >= (2,):
        if jupyterhub.version_info < (2, 2):
            access_token.roles = [db.query(orm.Role).filter_by(name="server").one()]
        else:
            access_token.scopes = [f"read:users!user={user.name}"]
    db.add(access_token)
    db.commit()

    # set some timestamps added in 0.9
    assert user.created
    assert admin.created
    # set last_activity
    user.last_activity = datetime.utcnow()
    spawner = user.orm_spawners['']
    spawner.started = datetime.utcnow()
    spawner.last_activity = datetime.utcnow()
    db.commit()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = 'sqlite:///jupyterhub.sqlite'

    populate_db(url)
