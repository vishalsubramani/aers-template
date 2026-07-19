import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from todo import TodoList


class TestCore(unittest.TestCase):
    def test_add_and_list(self):
        todos = TodoList()
        first = todos.add("write tutorial")
        self.assertEqual([i["title"] for i in todos.items()], ["write tutorial"])
        self.assertFalse(todos.items()[0]["done"])
        self.assertEqual(first, 1)

    def test_complete(self):
        todos = TodoList()
        item = todos.add("ship it")
        todos.complete(item)
        self.assertTrue(todos.items()[0]["done"])

    def test_rejects_empty_title(self):
        with self.assertRaises(ValueError):
            TodoList().add("   ")


if __name__ == "__main__":
    unittest.main()
