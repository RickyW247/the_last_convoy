"""Project-level checks: no star imports, README version and file list.

(That the game rules import without pygame is tested in test_headless_game.py.)
"""

import ast
import os
import re
import unittest

import main

from tests.helpers import GAME_DIR, project_python_files


class StructureTests(unittest.TestCase):
    def test_no_module_uses_a_star_import(self):
        for relative in project_python_files(include_tests=True):
            with open(os.path.join(GAME_DIR, relative), encoding="utf-8") as source:
                tree = ast.parse(source.read(), relative)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn("*", [alias.name for alias in node.names],
                                     f"{relative}: from {node.module} import *")


class ReadmeTests(unittest.TestCase):
    """The README is main.py's docstring."""

    @classmethod
    def setUpClass(cls):
        cls.doc = main.__doc__
        if not cls.doc:
            raise AssertionError("main.py has no README docstring (did it move? update tests/test_structure.py)")

    def test_readme_version_has_a_history_entry(self):
        version = re.search(r"Version: (\d+\.\d+)", self.doc).group(1)
        self.assertIn(f"- {version}:", self.doc, f"no version-history entry for {version}")

    def test_readme_has_the_standing_instructions(self):
        self.assertIn("without being asked", self.doc)

    def test_every_python_file_is_listed_in_the_readme(self):
        """Packages included: a file counts as listed by its path ("ui/convoy.py:") or its name ("convoy.py:")."""
        missing = []
        for relative in project_python_files():
            name = os.path.basename(relative)
            if name == "__init__.py":
                continue
            if f"{relative}:" not in self.doc and f"{name}:" not in self.doc:
                missing.append(relative)
        self.assertEqual(missing, [], "not listed in the README project files")
