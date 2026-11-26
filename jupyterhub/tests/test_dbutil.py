import ast
import json
import sys
from pathlib import Path
from subprocess import run

dbutil_cmd = [sys.executable, "-m", "jupyterhub.dbutil"]

_file = str(Path(__file__).resolve())


def run_dbutil(*args, check=True):
    p = run(
        dbutil_cmd + list(args),
        check=False,
        text=True,
        capture_output=True,
    )
    if check:
        if p.returncode != 0:
            print(p.stdout)
            print(p.stderr, file=sys.stderr)
            assert p.returncode == 0
    return p


def test_dbutil_noargs():
    p = run_dbutil(check=False)
    assert p.returncode
    assert "usage:" in p.stderr


def test_dbutil_help():
    p = run_dbutil("-h")
    assert "this help message" in p.stdout


def test_dbutil_shell():
    p = run_dbutil("shell")
    assert "Interpreter: IPython" in p.stdout


def test_dbutil_script(tmp_path):
    script = tmp_path / "myscript.py"
    script.write_text("print(db_url)")
    p = run_dbutil("script", str(script))
    assert p.stdout.strip() == "sqlite:///jupyterhub.sqlite"


def test_dbutil_script_argv(tmp_path):
    script = tmp_path / "myscript.py"
    script.write_text("import sys\nprint(sys.argv)")
    p = run_dbutil("script", str(script), "-x", "z")
    argv = ast.literal_eval(p.stdout)
    assert argv == [str(script), "-x", "z"]


def test_dbutil_script_ns():
    p = run_dbutil("script", _file, "a", "b")
    ns = json.loads(p.stdout)
    assert ns == {
        "sys.argv": [_file, "a", "b"],
        "db_url": "sqlite:///jupyterhub.sqlite",
        "db": "Session",
        "orm": "jupyterhub.orm",
        "session_factory": True,
    }


def test_dbutil_script_hub_args(tmp_path):
    script = tmp_path / "myscript.py"
    script.write_text("print(db_url)")
    p = run_dbutil("--db", "sqlite:///:memory:", "script", script)
    assert p.stdout.strip() == "sqlite:///:memory:"


def test_dbutil_alembic():
    run(["jupyterhub", "upgrade-db"], check=True)
    p = run_dbutil("alembic", "show", "head")
    assert "Revision ID" in p.stdout
    p = run_dbutil("alembic", "stamp", "head")


def main():
    # for use in testing dbutil script
    ns = globals()
    print(
        json.dumps(
            {
                "sys.argv": sys.argv,
                "db": type(ns.get("db")).__name__,
                "db_url": ns.get("db_url"),
                "session_factory": bool(ns.get("session_factory")),
                "orm": ns.get("orm").__name__,
            }
        )
    )


if __name__ == "__main__":
    main()
