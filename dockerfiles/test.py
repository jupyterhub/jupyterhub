import os

from jupyterhub._data import DATA_FILES_PATH

print(f"DATA_FILES_PATH={DATA_FILES_PATH}")

for sub_path in (
    "templates",
    "static/components",
    "static/css/style.min.css",
    "static/js/admin-react.js",
):
    path = os.path.join(DATA_FILES_PATH, sub_path)
    assert os.path.exists(path), path
