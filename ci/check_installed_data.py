#!/usr/bin/env python
# Check that installed package contains everything we expect


from pathlib import Path

import jupyterhub
from jupyterhub._data import DATA_FILES_PATH

print("Checking jupyterhub._data", end=" ")
print(f"DATA_FILES_PATH={DATA_FILES_PATH}", end=" ")
DATA_FILES_PATH = Path(DATA_FILES_PATH)
assert DATA_FILES_PATH.is_dir(), DATA_FILES_PATH
for subpath in (
    "templates/spawn.html",
    "static/css/style.min.css",
    "static/components/jquery/dist/jquery.js",
    "static/js/admin-react.js",
):
    path = DATA_FILES_PATH / subpath
    assert path.is_file(), path

print("OK")

print("Checking package_data", end=" ")
jupyterhub_path = Path(jupyterhub.__file__).parent.resolve()
for subpath in (
    "alembic.ini",
    "alembic/versions/833da8570507_rbac.py",
    "event-schemas/server-actions/v1.yaml",
    "singleuser/templates/page.html",
):
    path = jupyterhub_path / subpath
    assert path.is_file(), path

print("OK")
