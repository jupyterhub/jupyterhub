# -*- coding: utf-8 -*-
#
import os
import sys

# Set paths
sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# Minimal Sphinx version
needs_sphinx = '1.4'

# Sphinx extension modules
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'autodoc_traits',
    'sphinx_copybutton',
    'sphinx-jsonschema',
    'recommonmark',
]

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'JupyterHub'
copyright = u'2016, Project Jupyter team'
author = u'Project Jupyter team'

# Autopopulate version
from os.path import dirname

docs = dirname(dirname(__file__))
root = dirname(docs)
sys.path.insert(0, root)

import jupyterhub

# The short X.Y version.
version = '%i.%i' % jupyterhub.version_info[:2]
# The full version, including alpha/beta/rc tags.
release = jupyterhub.__version__

language = None
exclude_patterns = []
pygments_style = 'sphinx'
todo_include_todos = False

# Set the default role so we can use `foo` instead of ``foo``
default_role = 'literal'

# -- Source -------------------------------------------------------------

import recommonmark
from recommonmark.transform import AutoStructify

# -- Config -------------------------------------------------------------
from jupyterhub.app import JupyterHub
from docutils import nodes
from sphinx.directives.other import SphinxDirective
from contextlib import redirect_stdout
from io import StringIO

# create a temp instance of JupyterHub just to get the output of the generate-config
# and help --all commands.
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
        home_dir = os.environ['HOME']
        generated_config = generated_config.replace(home_dir, '$HOME', 1)
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
        buffer = StringIO()
        with redirect_stdout(buffer):
            jupyterhub_app.print_help('--help-all')
        all_help = buffer.getvalue()
        # post-process output
        home_dir = os.environ['HOME']
        all_help = all_help.replace(home_dir, '$HOME', 1)
        par = nodes.literal_block(text=all_help)
        return [par]


def setup(app):
    app.add_config_value('recommonmark_config', {'enable_eval_rst': True}, True)
    app.add_css_file('custom.css')
    app.add_transform(AutoStructify)
    app.add_directive('jupyterhub-generate-config', ConfigDirective)
    app.add_directive('jupyterhub-help-all', HelpAllDirective)


source_suffix = ['.rst', '.md']
# source_encoding = 'utf-8-sig'

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = 'pydata_sphinx_theme'

html_logo = '_static/images/logo/logo.png'
html_favicon = '_static/images/logo/favicon.ico'

# Paths that contain custom static files (such as style sheets)
html_static_path = ['_static']

htmlhelp_basename = 'JupyterHubdoc'

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # 'papersize': 'letterpaper',
    # 'pointsize': '10pt',
    # 'preamble': '',
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (
        master_doc,
        'JupyterHub.tex',
        u'JupyterHub Documentation',
        u'Project Jupyter team',
        'manual',
    )
]

# latex_logo = None
# latex_use_parts = False
# latex_show_pagerefs = False
# latex_show_urls = False
# latex_appendices = []
# latex_domain_indices = True


# -- manual page output -------------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [(master_doc, 'jupyterhub', u'JupyterHub Documentation', [author], 1)]

# man_show_urls = False


# -- Texinfo output -----------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        'JupyterHub',
        u'JupyterHub Documentation',
        author,
        'JupyterHub',
        'One line description of project.',
        'Miscellaneous',
    )
]

# texinfo_appendices = []
# texinfo_domain_indices = True
# texinfo_show_urls = 'footnote'
# texinfo_no_detailmenu = False


# -- Epub output --------------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright

# A list of files that should not be packed into the epub file.
epub_exclude_files = ['search.html']

# -- Intersphinx ----------------------------------------------------------

intersphinx_mapping = {'https://docs.python.org/3/': None}

# -- Read The Docs --------------------------------------------------------

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if on_rtd:
    # readthedocs.org uses their theme by default, so no need to specify it
    # build both metrics and rest-api, since RTD doesn't run make
    from subprocess import check_call as sh

    sh(['make', 'metrics', 'rest-api'], cwd=docs)

# -- Spell checking -------------------------------------------------------

try:
    import sphinxcontrib.spelling
except ImportError:
    pass
else:
    extensions.append("sphinxcontrib.spelling")

spelling_word_list_filename = 'spelling_wordlist.txt'
