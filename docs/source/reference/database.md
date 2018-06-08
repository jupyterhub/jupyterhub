# The Hub's Database

JupyterHub uses a database to store information about users, services, and other
data needed for operating the Hub.

## Default SQLite database

The default database for JupyterHub is a [SQLite](https://sqlite.org) database.
We have chosen SQLite as JupyterHub's default for its lightweight simplicity
in certain uses such as testing, small deployments and workshops.

For production systems, SQLite has some disadvantages when used with JupyterHub:

- `upgrade-db` may not work, and you may need to start with a fresh database
- `downgrade-db` **will not** work if you want to rollback to an earlier
  version, so backup the `jupyterhub.sqlite` file before upgrading

The sqlite documentation provides a helpful page about [when to use SQLite and
where traditional RDBMS may be a better choice](https://sqlite.org/whentouse.html).

## Using an RDBMS (PostgreSQL, MySQL)

When running a long term deployment or a production system, we recommend using
a traditional RDBMS database, such as [PostgreSQL](https://www.postgresql.org)
or [MySQL](https://www.mysql.com), that supports the SQL `ALTER TABLE`
statement.

## Notes and Tips

### SQLite

The SQLite database should not be used on NFS. SQLite uses reader/writer locks
to control access to the database. This locking mechanism might not work
correctly if the database file is kept on an NFS filesystem. This is because
`fcntl()` file locking is broken on many NFS implementations. Therefore, you
should avoid putting SQLite database files on NFS since it will not handle well
multiple processes which might try to access the file at the same time.

### PostgreSQL

We recommend using PostgreSQL for production if you are unsure whether to use
MySQL or PostgreSQL or if you do not have a strong preference. There is
additional configuration required for MySQL that is not needed for PostgreSQL.

### MySQL / MariaDB

- You should use the `pymysql` sqlalchemy provider (the other one, MySQLdb,
  isn't available for py3).
- You also need to set `pool_recycle` to some value (typically 60 - 300) 
  which depends on your  MySQL setup. This is necessary since MySQL kills
  connections serverside if they've been idle for a while, and the connection
  from the hub will be idle for longer than most connections. This behavior
  will lead to frustrating 'the connection has gone away' errors from
  sqlalchemy if `pool_recycle` is not set.
- If you use `utf8mb4` collation with MySQL earlier than 5.7.7 or MariaDB
  earlier than 10.2.1 you may get an `1709, Index column size too large` error.
  To fix this you need to set `innodb_large_prefix` to enabled and
  `innodb_file_format` to `Barracuda` to allow for the index sizes jupyterhub
  uses. `row_format` will be set to `DYNAMIC` as long as those options are set
  correctly. Later versions of MariaDB and MySQL should set these values by
  default, as well as have a default `DYNAMIC` `row_format` and pose no trouble
  to users.
