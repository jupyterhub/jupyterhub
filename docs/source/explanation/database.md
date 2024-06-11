(explanation:hub-database)=

# The Hub's Database

JupyterHub uses a database to store information about users, services, and other data needed for operating the Hub.
This is the **state** of the Hub.

## Why does JupyterHub have a database?

JupyterHub is a **stateful** application (more on that 'state' later).
Updating JupyterHub's configuration or upgrading the version of JupyterHub requires restarting the JupyterHub process to apply the changes.
We want to minimize the disruption caused by restarting the Hub process, so it can be a mundane, frequent, routine activity.
Storing state information outside the process for later retrieval is necessary for this, and one of the main thing databases are for.

A lot of the operations in JupyterHub are also **relationships**, which is exactly what SQL databases are great at.
For example:

- Given an API token, what user is making the request?
- Which users don't have running servers?
- Which servers belong to user X?
- Which users have not been active in the last 24 hours?

Finally, a database allows us to have more information stored without needing it all loaded in memory,
e.g. supporting a large number (several thousands) of inactive users.

## What's in the database?

The short answer of what's in the JupyterHub database is "everything."
JupyterHub's **state** lives in the database.
That is, everything JupyterHub needs to be aware of to function that _doesn't_ come from the configuration files, such as

- users, roles, role assignments
- state, urls of running servers
- Hashed API tokens
- Short-lived state related to OAuth flow
- Timestamps for when users, tokens, and servers were last used

### What's _not_ in the database

Not _quite_ all of JupyterHub's state is in the database.
This mostly involves transient state, such as the 'pending' transitions of Spawners (starting, stopping, etc.).
Anything not in the database must be reconstructed on Hub restart, and the only sources of information to do that are the database and JupyterHub configuration file(s).

## How does JupyterHub use the database?

JupyterHub makes some _unusual_ choices in how it connects to the database.
These choices represent trade-offs favoring single-process simplicity and performance at the expense of horizontal scalability (multiple Hub instances).

We often say that the Hub 'owns' the database.
This ownership means that we assume the Hub is the only process that will talk to the database.
This assumption enables us to make several caching optimizations that dramatically improve JupyterHub's performance (i.e. data written recently to the database can be read from memory instead of fetched again from the database) that would not work if multiple processes could be interacting with the database at the same time.

Database operations are also synchronous, so while JupyterHub is waiting on a database operation, it cannot respond to other requests.
This allows us to avoid complex locking mechanisms, because transaction races can only occur during an `await`, so we only need to make sure we've completed any given transaction before the next `await` in a given request.

:::{note}
We are slowly working to remove these assumptions, and moving to a more traditional db session per-request pattern.
This will enable multiple Hub instances and enable scaling JupyterHub, but will significantly reduce the number of active users a single Hub instance can serve.
:::

### Database performance in a typical request

Most authenticated requests to JupyterHub involve a few database transactions:

1. look up the authenticated user (e.g. look up token by hash, then resolve owner and permissions)
2. record activity
3. perform any relevant changes involved in processing the request (e.g. create the records for a running server when starting one)

This means that the database is involved in almost every request, but only in quite small, simple queries, e.g.:

- lookup one token by hash
- lookup one user by name
- list tokens or servers for one user (typically 1-10)
- etc.

### The database as a limiting factor

As a result of the above transactions in most requests, database performance is the _leading_ factor in JupyterHub's baseline requests-per-second performance, but that cost does not scale significantly with the number of users, active or otherwise.
However, the database is _rarely_ a limiting factor in JupyterHub performance in a practical sense, because the main thing JupyterHub does is start, stop, and monitor whole servers, which take far more time than any small database transaction, no matter how many records you have or how slow your database is (within reason).
Additionally, there is usually _very_ little load on the database itself.

By far the most taxing activity on the database is the 'list all users' endpoint, primarily used by the [idle-culling service](https://github.com/jupyterhub/jupyterhub-idle-culler).
Database-based optimizations have been added to make even these operations feasible for large numbers of users:

1. State filtering on [GET /hub/api/users?state=active](rest-api-get-users),
   which limits the number of results in the query to only the relevant subset (added in JupyterHub 1.3), rather than all users.
2. [Pagination](api-pagination) of all list endpoints, allowing the request of a large number of resources to be more fairly balanced with other Hub activities across multiple requests (added in 2.0).

:::{note}
It's important to note when discussing performance and limiting factors and that all of this only applies to requests to `/hub/...`.
The Hub and its database are not involved in most requests to single-user servers (`/user/...`), which is by design, and largely motivated by the fact that the Hub itself doesn't _need_ to be fast because its operations are infrequent and large.
:::

## Database backends

JupyterHub supports a variety of database backends via [SQLAlchemy][].
The default is sqlite, which works great for many cases, but you should be able to use many backends supported by SQLAlchemy.
Usually, this will mean PostgreSQL or MySQL, both of which are officially supported and well tested with JupyterHub, but others may work as well.
See [SQLAlchemy's docs][sqlalchemy-dialect] for how to connect to different database backends.
Doing so generally involves:

1. installing a Python package that provides a client implementation, and
2. setting [](JupyterHub.db_url) to connect to your database with the specified implementation

[sqlalchemy-dialect]: https://docs.sqlalchemy.org/en/20/dialects/
[sqlalchemy]: https://www.sqlalchemy.org

### Default backend: SQLite

The default database backend for JupyterHub is [SQLite](https://sqlite.org).
We have chosen SQLite as JupyterHub's default because it's simple (the 'database' is a single file) and ubiquitous (it is in the Python standard library).
It works very well for testing, small deployments, and workshops.

For production systems, SQLite has some disadvantages when used with JupyterHub:

- `upgrade-db` may not always work, and you may need to start with a fresh database
- `downgrade-db` **will not** work if you want to rollback to an earlier
  version, so backup the `jupyterhub.sqlite` file before upgrading (JupyterHub automatically creates a date-stamped backup file when upgrading sqlite)

The sqlite documentation provides a helpful page about [when to use SQLite and
where traditional RDBMS may be a better choice](https://sqlite.org/whentouse.html).

### Picking your database backend (PostgreSQL, MySQL)

When running a long term deployment or a production system, we recommend using a full-fledged relational database, such as [PostgreSQL](https://www.postgresql.org) or [MySQL](https://www.mysql.com), that supports the SQL `ALTER TABLE` statement, which is used in some database upgrade steps.

In general, you select your database backend with [](JupyterHub.db_url), and can further configure it (usually not necessary) with [](JupyterHub.db_kwargs).

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
MySQL or PostgreSQL or if you do not have a strong preference.
There is additional configuration required for MySQL that is not needed for PostgreSQL.

For example, to connect to a PostgreSQL database with psycopg2:

1. install psycopg2: `pip install psycopg2` (or `psycopg2-binary` to avoid compilation, which is [not recommended for production][psycopg2-binary])
2. set authentication via environment variables `PGUSER` and `PGPASSWORD`
3. configure [](JupyterHub.db_url):

   ```python
   c.JupyterHub.db_url = "postgresql+psycopg2://my-postgres-server:5432/my-db-name"
   ```

[psycopg2-binary]: https://www.psycopg.org/docs/install.html#psycopg-vs-psycopg-binary

### MySQL / MariaDB

- You should probably use the `pymysql` or `mysqlclient` sqlalchemy provider, or another backend [recommended by sqlalchemy](https://docs.sqlalchemy.org/en/20/dialects/mysql.html#dialect-mysql)
- You also need to set `pool_recycle` to some value (typically 60 - 300, JupyterHub will default to 60)
  which depends on your MySQL setup. This is necessary since MySQL kills
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

For example, to connect to a mysql database with mysqlclient:

1. install mysqlclient: `pip install mysqlclient`
2. configure [](JupyterHub.db_url):

   ```python
   c.JupyterHub.db_url = "mysql+mysqldb://myuser:mypassword@my-sql-server:3306/my-db-name"
   ```
