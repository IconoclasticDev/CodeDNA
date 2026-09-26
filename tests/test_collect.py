import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codedna.collect import collect_sources


class CollectTests(unittest.TestCase):
    @patch("codedna.collect.github_repository_files")
    def test_collection_pins_manifest_and_writes_python(self, repository_files):
        repository_files.return_value = (
            [{"name": "repo-sha/src/example.py", "content": "def value():\n    return 1\n"}],
            {
                "repository": "owner/repo",
                "commit_sha": "a" * 40,
                "non_python_skipped": 2,
                "unreadable_skipped": 0,
                "unsafe_skipped": 0,
            },
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources.csv"
            sources.write_text(
                "author_id,repository,ref,license_or_permission,collection_notes\n"
                "author_a,https://github.com/owner/repo,main,MIT,test fixture\n",
                encoding="utf-8",
            )
            result = collect_sources(sources, root / "dataset", root / "resolved.csv")
            written = root / "dataset" / "author_a" / "repo" / "src" / "example.py"
            written_content = written.read_text(encoding="utf-8")
            with (root / "resolved.csv").open(newline="", encoding="utf-8") as stream:
                resolved = list(csv.DictReader(stream))
        self.assertEqual(result["files"], 1)
        self.assertIn("def value", written_content)
        self.assertEqual(resolved[0]["commit_sha"], "a" * 40)
        repository_files.assert_called_once_with("https://github.com/owner/repo", ref="main")

    def test_collection_requires_permission_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources.csv"
            sources.write_text(
                "author_id,repository,license_or_permission\n"
                "author_a,https://github.com/owner/repo,\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Missing license"):
                collect_sources(sources, root / "dataset", root / "resolved.csv")


if __name__ == "__main__":
    unittest.main()
