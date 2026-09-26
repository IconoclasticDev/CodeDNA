import unittest

from codedna.features import FeatureExtractionError, extract_features


class FeatureTests(unittest.TestCase):
    def test_extracts_known_python_structure(self):
        result = extract_features("sample.py", "def total_values(values):\n    running_total = 0\n    for value in values:\n        running_total += value\n    return running_total\n")
        self.assertEqual(result.functions, 1)
        self.assertGreater(result.features["for_per_100_nodes"], 0)
        self.assertGreater(result.features["snake_case_ratio"], 0)
        self.assertGreaterEqual(result.features["cyclomatic_max"], 2)

    def test_type_annotations_are_counted(self):
        result = extract_features("typed.py", "def add(a: int, b: int) -> int:\n    return a + b\n")
        self.assertEqual(result.features["type_hint_ratio"], 1.0)

    def test_invalid_syntax_is_rejected(self):
        with self.assertRaises(FeatureExtractionError):
            extract_features("bad.py", "def broken(:\n")

    def test_empty_file_is_rejected(self):
        with self.assertRaises(FeatureExtractionError):
            extract_features("empty.py", "   \n")


if __name__ == "__main__":
    unittest.main()
