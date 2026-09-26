import tempfile
import unittest
from pathlib import Path

from codedna.reporting import benchmark_svg, confusion_matrix_svg, evidence_markdown, fold_csv, write_benchmark_artifacts


SAMPLE_RESULT = {
    "dataset": {"authors": 6, "files": 180, "pairs": 96},
    "evaluation": {
        "protocol": "grouped by claimed author",
        "summary": {
            "semantic_only": {"roc_auc": 0.70, "f1": 0.66, "f1_std": 0.06, "precision": 0.68, "recall": 0.65, "false_positive_rate": 0.23, "brier_score": 0.21},
            "engineered_only": {"roc_auc": 0.78, "f1": 0.73, "f1_std": 0.04, "precision": 0.75, "recall": 0.72, "false_positive_rate": 0.18, "brier_score": 0.17},
            "full_fusion": {"roc_auc": 0.84, "f1": 0.80, "f1_std": 0.03, "precision": 0.82, "recall": 0.79, "false_positive_rate": 0.12, "brier_score": 0.13},
        },
        "calibrated_thresholds": {
            "review": 0.35, "consistent": 0.72, "observed_false_review_rate": 0.08,
            "observed_impostor_consistent_rate": 0.09,
        },
        "selected_fusion": "full_fusion_logistic",
        "full_fusion_out_of_fold": {"tp": 38, "fp": 6, "fn": 10, "tn": 42},
        "folds": [
            {
                "held_out_authors": ["author_a", "author_b"],
                "test_pairs": 32,
                "full_fusion_logistic": {
                    "roc_auc": 0.84, "f1": 0.80, "precision": 0.82, "recall": 0.79,
                    "false_positive_rate": 0.12, "brier_score": 0.13,
                    "tp": 13, "fp": 3, "fn": 3, "tn": 13,
                },
            }
        ],
    },
    "limitation": "Prototype-scale evaluation.",
}


class ReportingTests(unittest.TestCase):
    def test_chart_contains_real_input_values(self):
        svg = benchmark_svg(SAMPLE_RESULT)
        self.assertIn("0.84", svg)
        self.assertIn("CodeDNA fusion", svg)
        self.assertTrue(svg.startswith("<svg"))

    def test_evidence_contains_protocol_and_thresholds(self):
        markdown = evidence_markdown(SAMPLE_RESULT)
        self.assertIn("grouped by claimed author", markdown)
        self.assertIn("0.350", markdown)
        self.assertIn("Prototype-scale evaluation", markdown)

    def test_confusion_matrix_uses_out_of_fold_counts(self):
        svg = confusion_matrix_svg(SAMPLE_RESULT)
        self.assertIn("out-of-fold confusion matrix", svg)
        self.assertIn(">42<", svg)
        self.assertIn(">6<", svg)

    def test_fold_csv_names_held_out_authors_and_metrics(self):
        content = fold_csv(SAMPLE_RESULT)
        self.assertIn("author_a;author_b", content)
        self.assertIn("full_fusion_logistic", content)
        self.assertIn("0.84", content)

    def test_artifacts_are_written_together(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = write_benchmark_artifacts(SAMPLE_RESULT, Path(directory))
            self.assertTrue(Path(paths["benchmark_chart"]).is_file())
            self.assertTrue(Path(paths["evidence_markdown"]).is_file())
            self.assertTrue(Path(paths["confusion_matrix"]).is_file())
            self.assertTrue(Path(paths["fold_metrics"]).is_file())


if __name__ == "__main__":
    unittest.main()
