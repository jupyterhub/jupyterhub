import sys
from pathlib import Path
from subprocess import run

from ruamel.yaml import YAML

yaml = YAML(typ="safe")

here = Path(__file__).absolute().parent
root = here.parent


def test_rest_api_version():
    version_py = root.joinpath("jupyterhub", "_version.py")
    rest_api_yaml = root.joinpath("docs", "source", "_static", "rest-api.yml")
    ns = {}
    with version_py.open() as f:
        exec(f.read(), {}, ns)
    jupyterhub_version = ns["__version__"]

    with rest_api_yaml.open() as f:
        rest_api = yaml.load(f)
        rest_api_version = rest_api["info"]["version"]

    assert jupyterhub_version == rest_api_version


def test_restapi_scopes():
    run([sys.executable, "source/rbac/generate-scope-table.py"], cwd=here, check=True)
    run(
        ['pre-commit', 'run', 'prettier', '--files', 'source/_static/rest-api.yml'],
        cwd=here,
        check=False,
    )
    run(
        [
            "git",
            "diff",
            "--no-pager",
            "--exit-code",
            str(here.joinpath("source", "_static", "rest-api.yml")),
        ],
        cwd=here,
        check=True,
    )
