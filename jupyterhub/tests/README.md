# Pytest-Asyncio and the JupyterHub Test Suite

When testing the various JupyterHub components and their various implementations, it sometimes becomes necessary to have a running instance of JupyterHub to test against.
The [`app`](https://github.com/jupyterhub/jupyterhub/blob/270b61992143b29af8c2fab90c4ed32f2f6fe209/jupyterhub/tests/conftest.py#L60) fixture mocks a JupyterHub application for use in testing by:

- enabling ssl if internal certificates are available
- creating an instance of [MockHub](https://github.com/jupyterhub/jupyterhub/blob/270b61992143b29af8c2fab90c4ed32f2f6fe209/jupyterhub/tests/mocking.py#L221) using any provided configurations as arguments
- initializing the mocked instance
- starting the mocked instance
- Finally, a registered finalizer function performs a cleanup and stops the mocked instance

The JupyterHub test suite uses the [pytest-asyncio plugin](https://pytest-asyncio.readthedocs.io/en/latest/) that handles [event-loop](https://docs.python.org/3/library/asyncio-eventloop.html) integration in [Tornado](https://www.tornadoweb.org/en/stable/) applications. This allows for the use of **top-level awaits** when calling async functions or [fixtures](https://docs.pytest.org/en/6.2.x/fixture.html#what-fixtures-are) during testing. All test functions and fixtures labelled as `async` will run on the same event loop.

With the introduction of top-level awaits, the use of the `io_loop` fixture of the [pytest-tornado plugin](https://www.tornadoweb.org/en/stable/ioloop.html) is no longer necessary. It was initially used to call coroutines. With the upgrades made to `pytest-asyncio`, this usage is now deprecated. It is now, only utilized within the JupyterHub test suite to ensure complete cleanup of resources used during testing such as open file descriptors. This is demonstrated in this [pull request](https://github.com/jupyterhub/jupyterhub/pull/4332).

One of the general goals of the [JupyterHub Pytest Plugin project](https://github.com/jupyterhub/pytest-jupyterhub) is to ensure the MockHub cleanup fully closes and stops all utilized resources during testing so the use of the `io_loop` fixture for teardown is not necessary. This was highlighted in this [issue](https://github.com/jupyterhub/pytest-jupyterhub/issues/30)

For more information on asyncio and event-loops, here are some resources:

- **Read**: [Introduction to the Python event loop](https://www.pythontutorial.net/python-concurrency/python-event-loop)
- **Read**: [Overview of Async IO in Python 3.7](https://stackabuse.com/overview-of-async-io-in-python-3-7)
- **Watch**: [Asyncio: Understanding Async / Await in Python](https://www.youtube.com/watch?v=bs9tlDFWWdQ)
- **Watch**: [Learn Python's AsyncIO #2 - The Event Loop](https://www.youtube.com/watch?v=E7Yn5biBZ58)
