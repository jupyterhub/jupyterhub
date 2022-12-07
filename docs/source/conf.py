# Configuration file for Sphinx to build our documentation to HTML.
#
# Configuration reference: https://www.sphinx-doc.org/en/master/usage/configuration.html
#
import contextlib
import datetime
import io
import os
import subprocess

from docutils import nodes
from sphinx.directives.other import SphinxDirective

import jupyterhub
from jupyterhub.app import JupyterHub

# -- Project information -----------------------------------------------------
# ref: https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
#
project = "JupyterHub"
author = "Project Jupyter Contributors"
copyright = f"{datetime.date.today().year}, {author}"


# -- General Sphinx configuration --------------------------------------------
# ref: https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
#
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "autodoc_traits",
    "sphinx_copybutton",
    "sphinx-jsonschema",
    "sphinxext.opengraph",
    "sphinxext.rediraffe",
    "myst_parser",
]
root_doc = "index"
source_suffix = [".md"]
# default_role let's use use `foo` instead of ``foo`` in rST
default_role = "literal"


# -- MyST configuration ------------------------------------------------------
# ref: https://myst-parser.readthedocs.io/en/latest/configuration.html
#
myst_heading_anchors = 2

myst_enable_extensions = [
    # available extensions: https://myst-parser.readthedocs.io/en/latest/syntax/optional.html
    "colon_fence",
    "deflist",
    "fieldlist",
    "substitution",
]

myst_substitutions = {
    # date example: Dev 07, 2022
    "date": datetime.date.today().strftime("%b %d, %Y").title(),
    "version": jupyterhub.__version__,
}


# -- Custom directives to generate documentation -----------------------------
# ref: https://myst-parser.readthedocs.io/en/latest/syntax/roles-and-directives.html
#
# We define custom directives to help us generate documentation using Python on
# demand when referenced from our documentation files.
#

# Create a temp instance of JupyterHub for use by two separate directive classes
# to get the output from using the "--generate-config" and "--help-all" CLI
# flags respectively.
#
jupyterhub_app = JupyterHub()


class ConfigDirective(SphinxDirective):
    """Generate the configuration file output for use in the documentation."""

    has_content = False
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self):
        # The generated configuration file for this version
        generated_config = jupyterhub_app.generate_config_file()
        # post-process output
        home_dir = os.environ["HOME"]
        generated_config = generated_config.replace(home_dir, "$HOME", 1)
        par = nodes.literal_block(text=generated_config)
        return [par]


class HelpAllDirective(SphinxDirective):
    """Print the output of jupyterhub help --all for use in the documentation."""

    has_content = False
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self):
        # The output of the help command for this version
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            jupyterhub_app.print_help("--help-all")
        all_help = buffer.getvalue()
        # post-process output
        home_dir = os.environ["HOME"]
        all_help = all_help.replace(home_dir, "$HOME", 1)
        par = nodes.literal_block(text=all_help)
        return [par]


def setup(app):
    app.add_css_file("custom.css")
    app.add_directive("jupyterhub-generate-config", ConfigDirective)
    app.add_directive("jupyterhub-help-all", HelpAllDirective)


# -- Read The Docs -----------------------------------------------------------
#
# Since RTD runs sphinx-build directly without running "make html", we run the
# pre-requisite steps for "make html" from here if needed.
#
if os.environ.get("READTHEDOCS"):
    docs = os.path.dirname(os.path.dirname(__file__))
    subprocess.check_call(["make", "metrics", "scopes"], cwd=docs)


# -- Spell checking ----------------------------------------------------------
# ref: https://sphinxcontrib-spelling.readthedocs.io/en/latest/customize.html#configuration-options
#
# The "sphinxcontrib.spelling" extension is optionally enabled if its available.
#
try:
    import sphinxcontrib.spelling  # noqa
except ImportError:
    pass
else:
    extensions.append("sphinxcontrib.spelling")
spelling_word_list_filename = "spelling_wordlist.txt"


# -- Options for HTML output -------------------------------------------------
# ref: https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
#
html_logo = "_static/images/logo/logo.png"
html_favicon = "_static/images/logo/favicon.ico"
html_static_path = ["_static"]

html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/jupyterhub/jupyterhub",
            "icon": "fab fa-github-square",
        },
        {
            "name": "Discourse",
            "url": "https://discourse.jupyter.org/c/jupyterhub/10",
            "icon": "fab fa-discourse",
        },
    ],
    "use_edit_page_button": True,
    "navbar_align": "left",
}
html_context = {
    "github_user": "jupyterhub",
    "github_repo": "jupyterhub",
    "github_version": "main",
    "doc_path": "docs/source",
}


# -- Options for linkcheck builder -------------------------------------------
# ref: https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-the-linkcheck-builder
#
linkcheck_ignore = [
    r"(.*)github\.com(.*)#",  # javascript based anchors
    r"(.*)/#%21(.*)/(.*)",  # /#!forum/jupyter - encoded anchor edge case
    r"https://github.com/[^/]*$",  # too many github usernames / searches in changelog
    "https://github.com/jupyterhub/jupyterhub/pull/",  # too many PRs in changelog
    "https://github.com/jupyterhub/jupyterhub/compare/",  # too many comparisons in changelog
]
linkcheck_anchors_ignore = [
    "/#!",
    "/#%21",
]


# -- Intersphinx -------------------------------------------------------------
# ref: https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#configuration
#
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "tornado": ("https://www.tornadoweb.org/en/stable/", None),
}
# -- Options for the opengraph extension -------------------------------------
# ref: https://github.com/wpilibsuite/sphinxext-opengraph#options
#
# ogp_site_url is set automatically by RTD
ogp_image = "_static/logo.png"
ogp_use_first_image = True


# -- Options for the rediraffe extension -------------------------------------
# ref: https://github.com/wpilibsuite/sphinxext-rediraffe#readme
#
# This extensions help us relocated content without breaking links. If a
# document is moved internally, a redirect like should be configured below to
# help us not break links.
#
rediraffe_branch = "main"
rediraffe_redirects = {
    # "old-file": "new-folder/new-file-name",
}
