import inspect
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(".."))
load_dotenv(os.path.join(os.path.abspath(".."), ".env"))

project = "Contacts REST API"
copyright = "2026, Ruslan Mirasov"
author = "Ruslan Mirasov"
release = "1.0"

extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon"]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

language = "uk"

html_theme = "nature"
html_static_path = []
html_theme_options = {"body_max_width": "none"}

autodoc_class_signature = "separated"
autodoc_typehints = "description"
autodoc_preserve_defaults = True
autodoc_member_order = "bysource"
autodoc_default_options = {
    "exclude-members": "__init__, model_config, metadata, registry"
}
autoclass_content = "class"
add_module_names = False
toc_object_entries = False

suppress_warnings = ["ref.ref"]


def add_own_init_docstring(app, what, name, obj, options, lines):
    """Додає до опису класу docstring його власного ``__init__``, без успадкованих."""
    init = obj.__dict__.get("__init__") if what == "class" else None
    own_init = init is not None and getattr(init, "__module__", "").startswith("src")
    if own_init and init.__doc__:
        lines.extend([""] + inspect.cleandoc(init.__doc__).splitlines())


def setup(app):
    app.connect("autodoc-process-docstring", add_own_init_docstring, priority=400)
