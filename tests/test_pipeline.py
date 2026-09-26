import unittest

from codedna.demo import CONSISTENT, HISTORY, REVIEW
from codedna.profile import build_profile, extract_file_set
from codedna.scoring import analyze_submission


class PipelineTests(unittest.TestCase):
    def test_profile_builds_from_valid_files(self):
        profile = build_profile("Test developer", HISTORY)
        self.assertEqual(profile["files_analyzed"], len(HISTORY))
        self.assertEqual(profile["name"], "Test developer")
        self.assertIn("lexical", profile["group_stability"])
        self.assertEqual(profile["representation_name"], "ast-token-hash-v1")

    def test_too_few_files_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "At least"):
            build_profile("Test", HISTORY[:2])

    def test_duplicates_are_removed(self):
        files, skipped, duplicates = extract_file_set([HISTORY[0], HISTORY[0], HISTORY[1]])
        self.assertEqual(len(files), 2)
        self.assertEqual(duplicates, 1)
        self.assertEqual(skipped, [])

    def test_non_python_file_is_skipped(self):
        files, skipped, _ = extract_file_set([{"name": "readme.txt", "content": "hello"}])
        self.assertEqual(files, [])
        self.assertEqual(len(skipped), 1)

    def test_score_is_bounded_and_explained(self):
        profile = build_profile("Test", HISTORY)
        report = analyze_submission(profile, CONSISTENT)
        self.assertGreaterEqual(report["score"], 0)
        self.assertLessEqual(report["score"], 100)
        self.assertEqual(len(report["top_deviations"]), 5)
        self.assertTrue(all(abs(item["deviation_score"]) <= 9.9 for item in report["top_deviations"]))
        self.assertTrue(all("scale_method" in item for item in report["top_deviations"]))
        self.assertIn(report["verdict"], {"Consistent", "Uncertain", "Review Recommended"})
        self.assertEqual(report["file_breakdown"], [])

    def test_multi_file_report_ranks_files_by_consistency(self):
        profile = build_profile("Test", HISTORY)
        mixed = [
            {"name": "familiar.py", "content": CONSISTENT[0]["content"]},
            {"name": "shifted.py", "content": REVIEW[0]["content"]},
        ]
        report = analyze_submission(profile, mixed)
        self.assertEqual(report["file_breakdown_total"], 2)
        self.assertEqual(len(report["file_breakdown"]), 2)
        self.assertLessEqual(report["file_breakdown"][0]["score"], report["file_breakdown"][1]["score"])
        self.assertEqual(report["file_breakdown"][0]["name"], "shifted.py")
        self.assertIn("surface_structure_gap", report["file_breakdown"][0])

    def test_function_review_map_ranks_engineered_deviation(self):
        profile = build_profile("Test", HISTORY)
        report = analyze_submission(profile, REVIEW)
        self.assertGreaterEqual(report["function_breakdown_total"], 3)
        self.assertLessEqual(len(report["function_breakdown"]), 12)
        first = report["function_breakdown"][0]
        self.assertIn("function", first)
        self.assertIn("strongest_feature", first)
        self.assertEqual(set(first["signals"]), {"lexical", "structural", "complexity"})
        self.assertTrue(all(0 <= value <= 100 for value in first["signals"].values()))
        self.assertGreaterEqual(
            first["deviation_index"], report["function_breakdown"][-1]["deviation_index"]
        )

    def test_demo_cases_produce_different_scores(self):
        profile = build_profile("Test", HISTORY)
        consistent = analyze_submission(profile, CONSISTENT)
        review = analyze_submission(profile, REVIEW)
        self.assertGreater(consistent["score"], review["score"])
        self.assertIn(consistent["verdict"], {"Consistent", "Uncertain"})
        self.assertEqual(review["verdict"], "Review Recommended")

    def test_invalid_submission_is_rejected(self):
        profile = build_profile("Test", HISTORY)
        with self.assertRaisesRegex(ValueError, "No valid"):
            analyze_submission(profile, [{"name": "bad.py", "content": "def x(:"}])

    def test_mismatched_representation_is_rejected(self):
        profile = build_profile("Test", HISTORY)
        profile["representation_name"] = "codebert-frozen-v1"
        with self.assertRaisesRegex(ValueError, "incompatible"):
            analyze_submission(profile, CONSISTENT)


if __name__ == "__main__":
    unittest.main()

