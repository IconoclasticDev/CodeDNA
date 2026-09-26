import tempfile
import unittest
from pathlib import Path

import numpy as np

from codedna.fusion import FusionModel, MLPFusionModel, load_model, train_logistic, train_mlp
from codedna.semantic import ast_token_vector, cosine_similarity
from codedna.train import build_pairs, calibrate_verdict_thresholds, grouped_evaluation, run as run_training


class FusionTests(unittest.TestCase):
    def test_logistic_model_learns_separable_examples(self):
        features = np.asarray([
            [0.9, 0.9, 0.8, 0.9, 0.0], [0.8, 0.9, 0.9, 0.8, -0.05],
            [0.2, 0.3, 0.2, 0.4, -0.1], [0.3, 0.2, 0.3, 0.3, 0.05],
        ])
        labels = np.asarray([1, 1, 0, 0])
        model = train_logistic(features, labels, epochs=600)
        self.assertGreater(model.predict_probability(features[0].tolist()), 0.8)
        self.assertLess(model.predict_probability(features[-1].tolist()), 0.2)

    def test_mlp_challenger_learns_and_round_trips(self):
        features = np.asarray([
            [0.95, 0.90, 0.88, 0.91, 0.02], [0.84, 0.92, 0.86, 0.89, -0.04],
            [0.18, 0.25, 0.20, 0.31, -0.05], [0.28, 0.19, 0.25, 0.22, 0.08],
        ])
        labels = np.asarray([1, 1, 0, 0])
        model = train_mlp(features, labels, epochs=900, dropout=0.0)
        self.assertGreater(model.predict_probability(features[0].tolist()), 0.75)
        self.assertLess(model.predict_probability(features[-1].tolist()), 0.25)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mlp.json"
            model.save(path)
            loaded = load_model(path)
        self.assertIsInstance(loaded, MLPFusionModel)
        self.assertAlmostEqual(model.predict_probability(features[0].tolist()), loaded.predict_probability(features[0].tolist()))

    def test_model_round_trip(self):
        model = FusionModel([1, 2, 3, 4, 5], -0.5, [0] * 5, [1] * 5, {"consistent": 0.7, "review": 0.4})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.json"
            model.save(path)
            loaded = FusionModel.load(path)
        self.assertAlmostEqual(model.predict_probability([0.2] * 5), loaded.predict_probability([0.2] * 5))
        self.assertEqual(loaded.representation, "ast-token-hash-v1")

    def test_ast_token_representation_is_normalized(self):
        vector = ast_token_vector("def add(a, b):\n    return a + b\n")
        self.assertAlmostEqual(sum(value * value for value in vector), 1.0)
        self.assertAlmostEqual(cosine_similarity(vector, vector), 1.0)

    def test_grouped_evaluation_holds_out_each_author(self):
        templates = {
            "alpha": "def total_{i}(values):\n    result = 0\n    for value in values:\n        result += value\n    return result + {i}\n",
            "beta": "def mapped{i}(values: list[int]) -> list[int]:\n    return [value * {n} for value in values if value > {i}]\n",
            "gamma": "def scan_{i}(values):\n    index = 0\n    while index < len(values):\n        if values[index] == {i}:\n            return index\n        index += 1\n    return -1\n",
            "delta": "def safe_{i}(value):\n    try:\n        if value and value > {i}:\n            return value / {n}\n    except (TypeError, ZeroDivisionError):\n        return None\n    return 0\n",
        }
        authors = {
            author: [
                {"name": f"{author}_{index}.py", "content": template.format(i=index, n=index + 1)}
                for index in range(6)
            ]
            for author, template in templates.items()
        }
        pairs = build_pairs(authors)
        result = grouped_evaluation(pairs)
        held_out = {author for fold in result["folds"] for author in fold["held_out_authors"]}
        self.assertEqual(held_out, set(authors))
        self.assertTrue(all("query_author" in pair and pair["query_author"] in authors for pair in pairs))
        self.assertTrue(all("leakage_check" in fold for fold in result["folds"]))
        self.assertIn("full_fusion", result["summary"])
        self.assertIn(result["selected_fusion"], {"full_fusion_logistic", "full_fusion_mlp"})
        self.assertLess(result["calibrated_thresholds"]["review"], result["calibrated_thresholds"]["consistent"])

    def test_threshold_calibration_creates_uncertainty_band(self):
        labels = np.asarray([1, 1, 1, 1, 0, 0, 0, 0])
        scores = np.asarray([0.95, 0.88, 0.80, 0.72, 0.40, 0.30, 0.20, 0.10])
        thresholds = calibrate_verdict_thresholds(labels, scores)
        self.assertLess(thresholds["review"], thresholds["consistent"])
        self.assertGreater(thresholds["uncertain_band_width"], 0)

    def test_overlapping_scores_are_absorbed_by_uncertainty(self):
        labels = np.asarray([1] * 10 + [0] * 10)
        scores = np.asarray([0.30, 0.38, 0.45, 0.52, 0.58, 0.63, 0.68, 0.72, 0.79, 0.86,
                             0.22, 0.35, 0.48, 0.55, 0.60, 0.66, 0.71, 0.76, 0.82, 0.90])
        thresholds = calibrate_verdict_thresholds(labels, scores, target_error=0.10)
        genuine = scores[labels == 1]
        impostor = scores[labels == 0]
        self.assertLessEqual(float(np.mean(genuine < thresholds["review"])), 0.10)
        self.assertLessEqual(float(np.mean(impostor >= thresholds["consistent"])), 0.10)
        self.assertGreater(thresholds["uncertain_band_width"], 0.25)

    def test_training_run_emits_model_metrics_chart_and_evidence(self):
        templates = {
            "alpha": "def total_{i}(values):\n    result = 0\n    for value in values:\n        result += value\n    return result + {i}\n",
            "beta": "def mapped{i}(values: list[int]) -> list[int]:\n    return [value * {n} for value in values if value > {i}]\n",
            "gamma": "def scan_{i}(values):\n    index = 0\n    while index < len(values):\n        if values[index] == {i}:\n            return index\n        index += 1\n    return -1\n",
            "delta": "def safe_{i}(value):\n    try:\n        if value and value > {i}:\n            return value / {n}\n    except (TypeError, ZeroDivisionError):\n        return None\n    return 0\n",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "dataset"
            for author, template in templates.items():
                folder = dataset / author
                folder.mkdir(parents=True)
                for index in range(6):
                    (folder / f"{index}.py").write_text(template.format(i=index, n=index + 1), encoding="utf-8")
            output = root / "evaluation" / "results.json"
            model_path = root / "artifacts" / "fusion.json"
            result = run_training(dataset, output, model_path)
            artifact_paths = [Path(path) for path in result["artifacts"].values()]
            self.assertTrue(output.is_file())
            self.assertTrue(model_path.is_file())
            self.assertTrue(all(path.is_file() for path in artifact_paths))
            self.assertIn(result["evaluation"]["selected_fusion"], {"full_fusion_logistic", "full_fusion_mlp"})
            self.assertIn("calibrated_operating_point", result["evaluation"])


if __name__ == "__main__":
    unittest.main()

