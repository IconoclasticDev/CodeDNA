import os
import unittest
from unittest.mock import patch

from codedna.codebert import _chunks
from codedna.representation import AST_PROVIDER, CODEBERT_PROVIDER, configured_provider, provider_status


class CodeBERTAdapterTests(unittest.TestCase):
    def test_chunking_prefers_module_function_and_class_boundaries(self):
        source = "import math\n\ndef add(a, b):\n    return a + b\n\nclass Box:\n    def value(self):\n        return 1\n"
        chunks = _chunks(source)
        self.assertEqual(len(chunks), 3)
        self.assertIn("import math", chunks[0])
        self.assertIn("def add", chunks[1])
        self.assertIn("class Box", chunks[2])

    def test_ast_provider_is_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(configured_provider(), AST_PROVIDER)
            self.assertTrue(provider_status()["available"])

    def test_codebert_provider_can_be_selected_explicitly(self):
        with patch.dict(os.environ, {"CODEDNA_REPRESENTATION": "codebert"}, clear=True):
            self.assertEqual(configured_provider(), CODEBERT_PROVIDER)
            self.assertEqual(provider_status()["configured"], CODEBERT_PROVIDER)


if __name__ == "__main__":
    unittest.main()

