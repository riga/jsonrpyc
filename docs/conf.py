from __future__ import annotations

import sys
import os

docsdir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(docsdir, "..", "src")))

import jsonrpyc as jp


project = jp.__name__
author = jp.__author__
copyright = jp.__copyright__
copyright = copyright[10:] if copyright.startswith("Copyright ") else copyright
copyright = copyright.split(",", 1)[0]
version = jp.__version__[:jp.__version__.index(".", 2)]
release = jp.__version__
language = "en"

html_static_path = ["_static"]
master_doc = "index"
source_suffix = ".rst"
pygments_style = "sphinx"
add_module_names = False
exclude_patterns: list[str] = []

html_title = f"{project} v{version}"
html_logo = "../assets/logo.png"
html_favicon = "../assets/favicon.ico"
html_theme = "sphinx_book_theme"
html_theme_options ={
    "home_page_in_toc": True,
    "show_navbar_depth": 2,
    "repository_url": "https://github.com/riga/jsonrpyc",
    "use_repository_button": True,
    "use_issues_button": True,
    "use_edit_page_button": True,
}

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosectionlabel",
    "autodocsumm",
    "myst_parser",
    "sphinx_lfs_content",
]

autodoc_default_options = {
    "member-order": "bysource",
    "show-inheritance": True,
}

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}


def setup(app):
    app.add_css_file("style.css")
