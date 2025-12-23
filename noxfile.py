import os.path

import nox

nox.options.reuse_existing_virtualenvs = True


@nox.session(default=False)
def docs(session):
    """
    Build the documentation and, optionally with '-- live', run a web server.
    """
    docs_dir = "docs"
    source_dir = os.path.join(docs_dir, "source")  # where conf.py is located
    data_dir = os.path.join(source_dir, "_data")
    output_dir = os.path.join(docs_dir, "_build")

    session.install("--editable", ".")
    session.install("-r", os.path.join(docs_dir, "requirements.txt"))

    doc_build_default_args = ["-b", "dirhtml", source_dir, output_dir]

    if "live" in session.posargs:
        # For live preview, sphinx-autobuild is used.
        # To avoid sphinx-autobuild be missing,
        # sphinx-autobuild is installed explicitly.
        session.install("sphinx-autobuild")
        cmd = ["sphinx-autobuild"]

        # Add relative paths to this if we ever need to ignore them
        autobuild_ignore = [output_dir, os.path.join(data_dir, "generated")]

        for folder in autobuild_ignore:
            cmd.extend(["--ignore", f"*/{folder}/*"])

        cmd.extend(doc_build_default_args)
        session.run(*cmd)
    else:
        session.run("sphinx-build", *doc_build_default_args)
