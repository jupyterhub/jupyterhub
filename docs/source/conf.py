# -*- coding: utf-8 -*-
#
import sys
import os
import shlex

# For conversion from markdown to html
import recommonmark.parser

# Set paths
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# Minimal Sphinx version
needs_sphinx = '1.4'

# Sphinx extension modules
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
]

templates_path = ['_templates']

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

# -- Source -------------------------------------------------------------

source_parsers = {
    '.md': 'recommonmark.parser.CommonMarkParser',
}

source_suffix = ['.rst', '.md']
#source_encoding = 'utf-8-sig'

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = 'sphinx_rtd_theme'

#html_theme_options = {}
#html_theme_path = []
#html_title = None
#html_short_title = None
#html_logo = None
#html_favicon = None

# Paths that contain custom static files (such as style sheets)
html_static_path = ['_static']

#html_extra_path = []
#html_last_updated_fmt = '%b %d, %Y'
#html_use_smartypants = True
#html_sidebars = {}
#html_additional_pages = {}
#html_domain_indices = True
#html_use_index = True
#html_split_index = False
#html_show_sourcelink = True
#html_show_sphinx = True
#html_show_copyright = True
#html_use_opensearch = ''
#html_file_suffix = None
#html_search_language = 'en'
#html_search_options = {'type': 'default'}
#html_search_scorer = 'scorer.js'
htmlhelp_basename = 'JupyterHubdoc'

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
#'papersize': 'letterpaper',
#'pointsize': '10pt',
#'preamble': '',
#'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  (master_doc, 'JupyterHub.tex', u'JupyterHub Documentation',
   u'Project Jupyter team', 'manual'),
]

#latex_logo = None
#latex_use_parts = False
#latex_show_pagerefs = False
#latex_show_urls = False
#latex_appendices = []
#latex_domain_indices = True


# -- manual page output -------------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'jupyterhub', u'JupyterHub Documentation',
     [author], 1)
]

#man_show_urls = False


# -- Texinfo output -----------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  (master_doc, 'JupyterHub', u'JupyterHub Documentation',
   author, 'JupyterHub', 'One line description of project.',
   'Miscellaneous'),
]

#texinfo_appendices = []
#texinfo_domain_indices = True
#texinfo_show_urls = 'footnote'
#texinfo_no_detailmenu = False


# -- Epub output --------------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright

# A list of files that should not be packed into the epub file.
epub_exclude_files = ['search.html']

# -- Intersphinx ----------------------------------------------------------

intersphinx_mapping = {'https://docs.python.org/': None}

# -- Read The Docs --------------------------------------------------------

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:
    # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
else:
    # readthedocs.org uses their theme by default, so no need to specify it
    # build rest-api, since RTD doesn't run make
    from subprocess import check_call as sh
    sh(['make', 'rest-api'], cwd=docs)

# -- Spell checking -------------------------------------------------------

try:
    import sphinxcontrib.spelling
except ImportError:
    pass
else:
    extensions.append("sphinxcontrib.spelling")

spelling_word_list_filename='spelling_wordlist.txt'
