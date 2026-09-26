import tempfile
import unittest
from pathlib import Path

from codedna.audit import audit_dataset, write_audit


class AuditTests(unittest.TestCase):
    def test_cross_author_duplicates_are_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for author in ("alpha", "beta"):
                folder = root / author
                folder.mkdir()
                (folder / "same.py").write_text("def same():\n    return 1\n", encoding="utf-8")
            rows, summary = audit_dataset(root)
        self.assertEqual(summary["cross_author_duplicate_hashes"], 1)
        self.assertTrue(all(row["status"] == "duplicate" for row in rows))

    def test_audit_writes_machine_readable_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "dataset"
            author = root / "alpha"
            author.mkdir(parents=True)
            (author / "valid.py").write_text("def value():\n    return 2\n", encoding="utf-8")
            result = write_audit(root, Path(directory) / "results")
            self.assertTrue(Path(result["manifest"]).is_file())
            self.assertTrue(Path(result["summary"]).is_file())


if __name__ == "__main__":
    unittest.main()

