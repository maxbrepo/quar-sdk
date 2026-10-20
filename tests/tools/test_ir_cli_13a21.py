import unittest
from unittest.mock import patch
from main import parse_c_layout_option, select_c_layout
from tooling.ir_build import CLayout

class IRCLI13A21Tests(unittest.TestCase):
    def test_single_layout(self):
        args, layout = parse_c_layout_option(["-f", "example.vq", "--c-layout", "single"])
        self.assertEqual(args, ["-f", "example.vq"])
        self.assertEqual(layout, CLayout.SINGLE)

    def test_split_layout(self):
        args, layout = parse_c_layout_option(["--c-layout", "split", "-l"])
        self.assertEqual(args, ["-l"])
        self.assertEqual(layout, CLayout.SPLIT)

    def test_invalid_layout(self):
        with self.assertRaises(ValueError):
            parse_c_layout_option(["-l", "--c-layout", "invalid"])

    def test_menu_selection(self):
        with patch("builtins.input", return_value="2"):
            self.assertEqual(select_c_layout(), CLayout.SPLIT)

if __name__ == "__main__":
    unittest.main()
