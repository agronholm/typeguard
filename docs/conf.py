#!/usr/bin/env python3
import pkg_resources

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

templates_path = ["_templates"]
source_suffix = ".rst"
master_doc = "index"
project = "Typeguard"
author = "Alex Grönholm"
copyright = "2015, " + author

v = pkg_resources.get_distribution("typeguard").parsed_version
version = v.base_version
release = v.public

language = None

exclude_patterns = ["_build"]
pygments_style = "sphinx"
highlight_language = "python3"
todo_include_todos = False
add_module_names = False

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
htmlhelp_basename = "typeguarddoc"

intersphinx_mapping = {"python": ("http://docs.python.org/3/", None)}
