import base64
import io
import unittest
import zipfile
from unittest.mock import patch

from codedna.ingest import GITHUB_RE, IngestionError, github_repository_files, python_files_from_base64, python_files_from_zip


def make_zip(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


class IngestionTests(unittest.TestCase):
    def test_reads_python_and_ignores_other_files(self):
        data = make_zip({"project/main.py": "print('ok')\n", "project/README.md": "hello"})
        files, stats = python_files_from_zip(data)
        self.assertEqual([item["name"] for item in files], ["project/main.py"])
        self.assertEqual(stats["non_python_skipped"], 1)

    def test_blocks_archive_traversal(self):
        data = make_zip({"../escape.py": "print('bad')", "safe.py": "print('ok')"})
        files, stats = python_files_from_zip(data)
        self.assertEqual([item["name"] for item in files], ["safe.py"])
        self.assertEqual(stats["unsafe_skipped"], 1)

    def test_base64_archive_validation(self):
        with self.assertRaises(IngestionError):
            python_files_from_base64("not base64!")

    @patch("codedna.ingest._github_raw_text")
    @patch("codedna.ingest._github_json")
    def test_github_link_scans_only_bounded_python_tree_files(self, github_json, raw_text):
        commit_sha = "a" * 40
        tree_sha = "b" * 40
        github_json.side_effect = [
            {"default_branch": "main"},
            {"sha": commit_sha, "commit": {"tree": {"sha": tree_sha}}},
            {
                "truncated": False,
                "tree": [
                    {"type": "blob", "path": "src/app.py", "size": 80},
                    {"type": "blob", "path": "README.md", "size": 20},
                    {"type": "blob", "path": "vendor/unsafe.py", "size": 30},
                    {"type": "blob", "path": "huge.py", "size": 1_000_001},
                ],
            },
        ]
        raw_text.return_value = "def run():\n    return 1\n"
        files, stats = github_repository_files("https://github.com/owner/repository")
        self.assertEqual([item["name"] for item in files], [f"repository-{commit_sha[:12]}/src/app.py"])
        self.assertEqual(stats["commit_sha"], commit_sha)
        self.assertEqual(stats["selected_python_files"], 1)
        self.assertEqual(stats["unsafe_skipped"], 1)
        self.assertEqual(stats["unreadable_skipped"], 1)
        raw_text.assert_called_once_with("owner", "repository", commit_sha, "src/app.py", 15)
    def test_github_url_is_strictly_allow_listed(self):
        self.assertIsNotNone(GITHUB_RE.fullmatch("https://github.com/openai/example"))
        self.assertIsNone(GITHUB_RE.fullmatch("https://github.com.evil.invalid/openai/example"))
        self.assertIsNone(GITHUB_RE.fullmatch("http://github.com/openai/example"))


if __name__ == "__main__":
    unittest.main()


