#!/usr/bin/env python
# Check that installed package contains everything we expect


import os

from jupyterhub._data import DATA_FILES_PATH

print("Checking jupyterhub._data")
print(f"DATA_FILES_PATH={DATA_FILES_PATH}")
assert os.path.exists(DATA_FILES_PATH), DATA_FILES_PATH
for subpath in (
    "templates/page.html",
    "static/css/style.min.css",
    "static/components/jquery/dist/jquery.js",
    "static/js/admin-react.js",
):
    path = os.path.join(DATA_FILES_PATH, subpath)
    assert os.path.exists(path), path
print("OK")
