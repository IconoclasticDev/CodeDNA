import tempfile
import unittest
from pathlib import Path

from codedna.evidence import EvidenceBuildError, build_evidence_pack


TEMPLATES = {
    "alpha": "def total_{i}(values):\n    result = 0\n    for value in values:\n        result += value\n    return result + {i}\n",
    "beta": "def mapped{i}(values: list[int]) -> list[int]:\n    return [value * {n} for value in values if value > {i}]\n",
    "gamma": "def scan_{i}(values):\n    index = 0\n    while index < len(values):\n        if values[index] == {i}:\n            return index\n        index += 1\n    return -1\n",
    "delta": "def safe_{i}(value):\n    try:\n        if value and value > {i}:\n            return value / {n}\n    except (TypeError, ZeroDivisionError):\n        return None\n    return 0\n",
}


class EvidencePackTests(unittest.TestCase):
    def test_rejects_dataset_that_fails_audit_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "dataset"
            folder = dataset / "only_author"
            folder.mkdir(parents=True)
            (folder / "one.py").write_text("value = 1\n", encoding="utf-8")
            with self.assertRaisesRegex(EvidenceBuildError, "at least four authors"):
                build_evidence_pack(dataset, root / "evaluation", root / "model.json")

    def test_builds_checksummed_evidence_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "dataset"
            for author, template in TEMPLATES.items():
                folder = dataset / author
                folder.mkdir(parents=True)
                for index in range(6):
                    (folder / f"{index}.py").write_text(template.format(i=index, n=index + 1), encoding="utf-8")
            pack = build_evidence_pack(dataset, root / "evaluation", root / "model.json")
            self.assertEqual(pack["status"], "complete")
            self.assertEqual(pack["audit"]["authors_found"], 4)
            self.assertTrue(Path(pack["manifest_path"]).is_file())
            self.assertIn("confusion_matrix", pack["artifacts"])
            self.assertEqual(len(pack["artifacts"]["results"]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
