import sys

c = get_config()  # noqa

c.JupyterHub.services = [
    {
        'name': 'grades',
        'url': 'http://127.0.0.1:10101',
        'command': [sys.executable, './grades.py'],
        'oauth_client_allowed_scopes': [
            'custom:grades:write',
            'custom:grades:read',
        ],
    },
]

c.JupyterHub.custom_scopes = {
    "custom:grades:read": {
        "description": "read-access to all grades",
    },
    "custom:grades:write": {
        "description": "Enter new grades",
        "subscopes": ["custom:grades:read"],
    },
}

c.JupyterHub.load_roles = [
    {
        "name": "user",
        # grant all users access to services
        "scopes": ["access:services", "self"],
    },
    {
        "name": "grader",
        # grant graders access to write grades
        "scopes": ["custom:grades:write"],
        "users": ["grader"],
    },
    {
        "name": "instructor",
        # grant instructors access to read, but not write grades
        "scopes": ["custom:grades:read"],
        "users": ["instructor"],
    },
]

c.JupyterHub.allowed_users = {"instructor", "grader", "student"}
# dummy spawner and authenticator for testing, don't actually use these!
c.JupyterHub.authenticator_class = 'dummy'
c.JupyterHub.spawner_class = 'simple'
c.JupyterHub.ip = '127.0.0.1'  # let's just run on localhost while dummy auth is enabled
c.JupyterHub.log_level = 10
