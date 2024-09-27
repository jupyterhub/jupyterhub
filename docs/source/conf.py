# Configuration file for Sphinx to build our documentation to HTML.
#
# Configuration reference: https://www.sphinx-doc.org/en/master/usage/configuration.html
#
import contextlib
import datetime
import io
import os
import re
import subprocess
from pathlib import Path
from urllib.request import urlretrieve

from docutils import nodes
from ruamel.yaml import YAML
from sphinx.directives.other import SphinxDirective
from sphinx.util import logging

import jupyterhub
from jupyterhub.app import JupyterHub

logger = logging.getLogger(__name__)
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
    "jupyterhub_sphinx_theme",
    "myst_parser",
]
root_doc = "index"
source_suffix = [".md"]
# default_role let's use use `foo` instead of ``foo`` in rST
default_role = "literal"

docs = Path(__file__).parent.parent.absolute()
docs_source = docs / "source"
rest_api_yaml = docs_source / "_static" / "rest-api.yml"


# -- MyST configuration ------------------------------------------------------
# ref: https://myst-parser.readthedocs.io/en/latest/configuration.html
#
myst_heading_anchors = 2

myst_enable_extensions = [
    # available extensions: https://myst-parser.readthedocs.io/en/latest/syntax/optional.html
    "attrs_inline",
    "colon_fence",
    "deflist",
    "fieldlist",
    "substitution",
]

myst_substitutions = {
    # date example: Dev 07, 2022
    "date": datetime.date.today().strftime("%b %d, %Y").title(),
    "node_min": "12",
    "python_min": "3.8",
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


class RestAPILinksDirective(SphinxDirective):
    """Directive to populate link targets for the REST API

    The resulting nodes resolve xref targets,
    but are not actually rendered in the final result
    which is handled by a custom template.
    """

    has_content = False
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self):
        targets = []
        yaml = YAML(typ="safe")
        with rest_api_yaml.open() as f:
            api = yaml.load(f)
        for path, path_spec in api["paths"].items():
            for method, operation in path_spec.items():
                operation_id = operation.get("operationId")
                if not operation_id:
                    logger.warning(f"No operation id for {method} {path}")
                    continue
                # 'id' is the id on the page (must match redoc anchor)
                # 'name' is the name of the ref for use in our documents
                target = nodes.target(
                    ids=[f"operation/{operation_id}"],
                    names=[f"rest-api-{operation_id}"],
                )
                targets.append(target)
                self.state.document.note_explicit_target(target, target)

        return targets


templates_path = ["_templates"]


def stage_redoc_js(app, exception):
    """Download redoc.js to our static files"""
    if app.builder.name != "html":
        logger.info(f"Skipping redoc download for builder: {app.builder.name}")
        return

    out_static = Path(app.builder.outdir) / "_static"

    redoc_version = "2.1.3"
    redoc_url = (
        f"https://cdn.redoc.ly/redoc/v{redoc_version}/bundles/redoc.standalone.js"
    )
    dest = out_static / "redoc.js"
    if not dest.exists():
        logger.info(f"Downloading {redoc_url} -> {dest}")
        urlretrieve(redoc_url, dest)

    # stage fonts for redoc from google fonts
    fonts_css_url = "https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700"
    fonts_css_file = out_static / "redoc-fonts.css"
    fonts_dir = out_static / "fonts"
    fonts_dir.mkdir(exist_ok=True)
    if not fonts_css_file.exists():
        logger.info(f"Downloading {fonts_css_url} -> {fonts_css_file}")
        urlretrieve(fonts_css_url, fonts_css_file)

    # For each font external font URL,
    # download the font and rewrite to a local URL
    # The downloaded TTF fonts have license info in their metadata
    with open(fonts_css_file) as f:
        fonts_css = f.read()

    fonts_css_changed = False
    for font_url in re.findall(r'url\((https?[^\)]+)\)', fonts_css):
        fonts_css_changed = True
        filename = font_url.rpartition("/")[-1]
        dest = fonts_dir / filename
        local_url = str(dest.relative_to(fonts_css_file.parent))
        fonts_css = fonts_css.replace(font_url, local_url)
        if not dest.exists():
            logger.info(f"Downloading {font_url} -> {dest}")
            urlretrieve(font_url, dest)

    if fonts_css_changed:
        # rewrite font css with local URLs
        with open(fonts_css_file, "w") as f:
            logger.info(f"Rewriting URLs in {fonts_css_file}")
            f.write(fonts_css)


def setup(app):
    app.connect("build-finished", stage_redoc_js)
    app.add_css_file("custom.css")
    app.add_directive("jupyterhub-generate-config", ConfigDirective)
    app.add_directive("jupyterhub-help-all", HelpAllDirective)
    app.add_directive("jupyterhub-rest-api-links", RestAPILinksDirective)


# -- Read The Docs -----------------------------------------------------------
#
# Since RTD runs sphinx-build directly without running "make html", we run the
# pre-requisite steps for "make html" from here if needed.
#
if os.environ.get("READTHEDOCS"):
    subprocess.check_call(["make", "metrics", "scopes"], cwd=str(docs))


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

html_theme = "jupyterhub_sphinx_theme"
html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/jupyterhub/jupyterhub",
            "icon": "fa-brands fa-github",
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
    r"https?://(.*\.)?example\.(org|com)(/.*)?",  # example links
    r"https://github.com/[^/]*$",  # too many github usernames / searches in changelog
    "https://github.com/jupyterhub/jupyterhub/pull/",  # too many PRs in changelog
    "https://github.com/jupyterhub/jupyterhub/compare/",  # too many comparisons in changelog
    "https://schema.jupyter.org/jupyterhub/.*",  # schemas are not published yet
    r"https?://(localhost|127.0.0.1).*",  # ignore localhost references in auto-links
    r"https://linux.die.net/.*",  # linux.die.net seems to block requests from CI with 403 sometimes
    # don't check links to unpublished advisories
    r"https://github.com/jupyterhub/jupyterhub/security/advisories/.*",
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
    "jupyter-server": ("https://jupyter-server.readthedocs.io/en/stable/", None),
    "nbgitpuller": ("https://nbgitpuller.readthedocs.io/en/latest", None),
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
# This extension helps us relocate content without breaking links. If a
# document is moved internally, a redirect link should be configured as below to
# help us not break links.
#
# The workflow for adding redirects can be as follows:
# 1. Change "rediraffe_branch" below to point to the commit/ branch you
#    want to base off the changes.
# 2. Option 1: run "make rediraffecheckdiff"
#       a. Analyze the output of this command.
#       b. Manually add the redirect entries to the "redirects.txt" file.
#    Option 2: run "make rediraffewritediff"
#       a. rediraffe will then automatically add the obvious redirects to redirects.txt.
#       b. Analyze the output of the command for broken links.
#       c. Check the "redirects.txt" file for any files that were moved/ renamed but are not listed.
#       d. Manually add the redirects that have been mised by the automatic builder to "redirects.txt".
#    Option 3: Do not use the commands above and, instead, do everything manually - by taking
#    note of the files you have moved or renamed and adding them to the "redirects.txt" file.
#
# If you are basing changes off another branch/ commit, always change back
# rediraffe_branch to main before pushing your changes upstream.
#
rediraffe_branch = os.environ.get("REDIRAFFE_BRANCH", "main")
rediraffe_redirects = "redirects.txt"

# allow 80% match for autogenerated redirects
rediraffe_auto_redirect_perc = 80

# rediraffe_redirects = {
# "old-file": "new-folder/new-file-name",
# }
