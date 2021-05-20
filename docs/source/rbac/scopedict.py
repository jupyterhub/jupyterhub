"""Scope definitions"""


def get_scope_dict():
    """Returns a nested dictionary of all available scopes:

    {scopename: {'description': description,
                 'subscopes': [immediate subscopes]},
    }

    without 'subscopes' key if the scope has no subscopes.
    """
    scope_dict = {
        '(no_scope)': {'description': 'Allows for only identifying the owning entity.'},
        'self': {
            'description': 'Metascope, grants access to user’s own resources only; resolves to (no_scope) for services.'
        },
        'all': {
            'description': 'Metascope, valid for tokens only. Grants access to everything that the token’s owning entity can access.'
        },
        'admin:users': {
            'description': 'Grants read, write, create and delete access to users and their authentication state but not their servers or tokens.',
            'subscopes': ['admin:users:auth_state', 'users'],
        },
        'admin:users:auth_state': {
            'description': 'Grants access to users’ authentication state only.'
        },
        'users': {
            'description': 'Grants read and write permissions to users’ models apart from servers, tokens and authentication state.',
            'subscopes': ['read:users', 'users:activity'],
        },
        'read:users': {
            'description': 'Read-only access to users’ models apart from servers, tokens and authentication state.',
            'subscopes': [
                'read:users:name',
                'read:users:groups',
                'read:users:activity',
                'read:users:roles',
            ],
        },
        'read:users:name': {'description': 'Read-only access to users’ names.'},
        'read:users:groups': {'description': 'Read-only access to users’ group names.'},
        'read:users:roles': {'description': 'Read-only access to users’ role names.'},
        'read:users:activity': {
            'description': 'Read-only access to users’ last activity.'
        },
        'users:activity': {
            'description': 'Grants access to read and post users’ last activity only.',
            'subscopes': ['read:users:activity'],
        },
        'admin:users:servers': {
            'description': 'Grants read, start/stop, create and delete permissions to users’ servers and their state.',
            'subscopes': ['admin:users:server_state', 'users:servers'],
        },
        'admin:users:server_state': {
            'description': 'Grants access to servers’ state only.'
        },
        'users:servers': {
            'description': 'Allows for starting/stopping users’ servers in addition to read access to their models. Does not include the server state.',
            'subscopes': ['read:users:servers'],
        },
        'read:users:servers': {
            'description': 'Read-only access to users’ names and their server models. Does not include the server state.',
            'subscopes': ['read:users:name'],
        },
        'users:tokens': {
            'description': 'Grants read, write, create and delete permissions to users’ tokens.',
            'subscopes': ['read:users:tokens'],
        },
        'read:users:tokens': {'description': 'Read-only access to users’ tokens.'},
        'admin:groups': {
            'description': 'Grants read, write, create and delete access to groups.',
            'subscopes': ['groups'],
        },
        'groups': {
            'description': 'Grants read and write permissions to groups, including adding/removing users to/from groups.',
            'subscopes': ['read:groups'],
        },
        'read:groups': {'description': 'Read-only access to groups’ models.'},
        'read:services': {
            'description': 'Read-only access to service models.',
            'subscopes': ['read:services:name', 'read:services:roles'],
        },
        'read:services:name': {'description': 'Read-only access to service names.'},
        'read:services:roles': {
            'description': 'Read-only access to service role names.'
        },
        'read:hub': {
            'description': 'Read-only access to detailed information about the Hub.'
        },
        'proxy': {
            'description': 'Allows for obtaining information about the proxy’s routing table, for syncing the Hub with proxy and notifying the Hub about a new proxy.'
        },
        'shutdown': {'description': 'Grants access to shutdown the hub.'},
    }

    return scope_dict
