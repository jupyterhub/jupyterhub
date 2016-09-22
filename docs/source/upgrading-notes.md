# Upgrading JupyterHub and its databases

## Definitions
db type: sqlite, postgres, mysql, others???
db fields: individual fields in a database table

## Basic use cases
- [ ] Simple upgrade - no database fields changed; no db type change
- [ ] Field changes  - database fields added, deleted or changed by a new JHub release/functionality; no db type change

## More complex use cases
- [ ] Field changes - database fields added, deleted or changed by user; no db type change
- [ ] db type change (i.e. sqlite to postgres) - fields may or may not change; db type does change

## Process
- Remind admins to back up Hub databases
- Possibly remind admins to make sure single user notebook data is saved/backed up
- Admin notify users (if desired) of planned upgrade

**Multi-step upgrade vs all at once**??
- Migrate database type (Hub at same release level) user-initiated
- Add/change/delete fields (Hub at same release level) user-initiated
- Add/change/delete files (Hub initiated - in prep for JHub release upgrade)
- Upgrade Hub to 0.7 after

- Upgrade/changes to: CHP, authenticators, spawners

## Other topics
- limitations of sqlite upgrade
- upgrade hub first or upgrade db first???

## Tools

### Using alembic for database migrations

[Alembic][] ([docs for alembic][]) provides change management scripts for a
relational database, using [SQLAlchemy][] as the underlying engine. This
section will explain how alembic is used to upgrade JupyterHub's database.

Looking at the JupyterHub source code from the root of the repo, we see:

- `jupyterhub/alembic.ini` This file contains configuration information for
  the database. It is used when the `alembic` command is run to access the
  location of the change management scripts.
- `jupyterhub/alembic` This directory contains the migration
  environment used by alembic. The `env.py` file in this directory is a
  Python file that is run when alembic does a database migration and may be
  customized if necessary.
  




[Alembic]: https://bitbucket.org/zzzeek/alembic
[docs for alembic]: http://alembic.zzzcomputing.com/en/latest/
[SQLAlchemy]: http://www.sqlalchemy.org

- scripts
- db tools
