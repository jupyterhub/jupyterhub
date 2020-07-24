#!/usr/bin/env python
"""Extend regular notebook server to be aware of multiuser things."""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from notebook.auth.login import LoginHandler
from notebook.auth.logout import LogoutHandler
from notebook.base.handlers import IPythonHandler
from notebook.notebookapp import NotebookApp

from .mixins import make_singleuser_app

SingleUserNotebookApp = make_singleuser_app(
    NotebookApp=NotebookApp,
    LoginHandler=LoginHandler,
    LogoutHandler=LogoutHandler,
    BaseHandler=IPythonHandler,
)

main = SingleUserNotebookApp.launch_instance

if __name__ == '__main__':
    main()
