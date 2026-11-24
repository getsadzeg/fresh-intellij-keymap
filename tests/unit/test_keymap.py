import json
import os
import string
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tests", "e2e"))
from cases import CASES
from keys import fresh_combo

MODIFIERS = {"super", "alt", "ctrl", "shift"}
KEYS = (set(string.ascii_lowercase) | set(string.digits) | set("[]/,.;'-=`\\ ")
        | {"Backspace", "Enter", "Tab", "Escape", "Delete", "Up", "Down", "Left", "Right",
           "Home", "End", "PageUp", "PageDown"} | {f"F{n}" for n in range(1, 13)})


class KeymapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "keymap.json")) as f:
            cls.rows = json.load(f)

    def test_is_a_non_empty_list_of_objects(self):
        self.assertIsInstance(self.rows, list)
        self.assertTrue(self.rows)
        for row in self.rows:
            self.assertEqual(set(row), {"intellij", "key", "modifiers", "action"}, row)

    def test_fields_are_valid(self):
        for row in self.rows:
            with self.subTest(row=row):
                self.assertTrue(row["intellij"].strip())
                self.assertTrue(row["action"].strip())
                self.assertIn(row["key"], KEYS)
                self.assertIsInstance(row["modifiers"], list)
                self.assertLessEqual(set(row["modifiers"]), MODIFIERS)
                self.assertEqual(len(row["modifiers"]), len(set(row["modifiers"])))

    def test_no_duplicate_shortcuts(self):
        seen = {}
        for row in self.rows:
            combo = (row["key"], frozenset(row["modifiers"]))
            self.assertNotIn(combo, seen, f"{row['intellij']} and {seen.get(combo)} share a shortcut")
            seen[combo] = row["intellij"]

    def test_every_row_has_an_e2e_case(self):
        for row in self.rows:
            combo = fresh_combo(row["key"], row["modifiers"])
            with self.subTest(row=row["intellij"]):
                for kind in ("plugin", "partial"):
                    matching = [c for c in CASES if c.kind == kind and (c.shortcut, c.action) == (combo, row["action"])]
                    self.assertLessEqual(len(matching), 1, [c.name for c in matching])
                self.assertTrue(any(c.kind in ("plugin", "partial") and (c.shortcut, c.action) == (combo, row["action"])
                                    for c in CASES))

    def test_every_plugin_case_maps_to_a_row(self):
        rows = {(fresh_combo(r["key"], r["modifiers"]), r["action"]) for r in self.rows}
        for case in CASES:
            if case.kind in ("plugin", "partial"):
                with self.subTest(case=case.name):
                    self.assertIn((case.shortcut, case.action), rows)


if __name__ == "__main__":
    unittest.main()
