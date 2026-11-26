(howto-database)=

# Working with the JupyterHub database

JupyterHub stores its state in an SQL database.

Sometimes, you might want to interact directly with the JupyterHub database.
You can do this with any standard SQL tools for your database,
but JupyterHub also provides some utilities to make this a bit more convenient.

These are under the `python3 -m jupyterhub.dbutil` command.

Most operations should be fine, but particularly modifications to users might not be reflected into the JupyterHub state right away,
and restarting the Hub process after modifications should reconcile any inconsistencies.

```{warning}
Directly modifying the database carries some risks,
make sure you either know what you're doing, back up the database, or both,
before making significant manual changes.
```

## general arguments

In general, the argument structure looks like:

```bash
python3 -m jupyterhub.dbutil [jupyterhub arguments] COMMAND [command arguments]
```

where COMMAND is one of `shell`, `script`, `alembic`,
`[jupyterhub arguments]` are any arguments to pass to JupyterHub (only db and logging-related arguments will have an effect),
and `[command arguments]` are command-specific.

## dbutil shell

The most useful command to inspect the database is

```bash
python3 -m jupyterhub.dbutil shell
```

will launch you into an interactive shell (IPython, if available),
with the namespace populated with:

| name            | note                                  |
| --------------- | ------------------------------------- |
| db              | a connected db session                |
| db_url          | the url for the database              |
| session_factory | a callable to return a new db session |
| orm             | same as `from jupyterhub import orm`  |

CLI arguments passed after `shell` are passed to IPython.

In a shell session, you can run [SQLAlchemy queries](https://docs.sqlalchemy.org/en/21/tutorial/), e.g. getting the 5 most recently active users:

```
In [1]: db.query(orm.User).order_by(orm.User.last_activity.desc()).limit(5).all()
Out[1]:
[<User(test 0/2 running)>,
 <User(admin 0/0 running)>,
 <User(test-27 0/0 running)>,
 <User(test-91 0/0 running)>,
 <User(test-73 0/0 running)>]
```

## dbutil script

```{versionadded} 6.3

```

If you have scripted operations that you want to execute instead of an interactive session,
you can use

```
python3 -m jupyterhub.dbutil script ./yourscript.py
```

The script will have the same `db`, `orm`, etc. names injected, but if you want to make sure your script passes linters,
it can import these names:

```python
from jupyterhub import orm
from jupyterhub.dbutil import db
```

If you want to pipe commands, use `-` for the script path:

```
cat yourscript | python3 -m jupyterhub.dbutil script -
```

which is especially useful when your hub installation is in a remote container, such as when running with kubernetes.
For example, to run a local script in a typical `hub` pod:

```bash
cat myscript.py | kubectl exec -i deployments/hub -c hub -- python3 -m jupyterhub.dbutil script -
```

## dbutil alembic

Less likely to be used, is

```
python3 -m jupyterhub.dbutil alembic [alembic arguments]
```

This passes through arguments to [alembic's](https://alembic.sqlalchemy.org/) many arguments, if you have reason to run alembic's commands.
Alembic is the tool we use to manage database schema migrations across JupyterHub upgrades.

Most often, this is used during JupyterHub development to initialize new database schema revisions after modifying `jupyterhub.orm`, for example:

```bash
python3 -m jupyterhub.dbutil alembic revision --autogenerate -m "6.2: add oauth_code.nonce"
```
