# Evaluation procedure

## Dataset layout

```text
dataset/
  author_a/
    repository_one/*.py
  author_b/
    repository_two/*.py
  author_c/
    ...
  author_d/
    ...
```

Run:

```powershell
python -m codedna.collect sources.csv --dataset work/dataset --manifest work/evaluation/resolved_sources.csv
python -m codedna.evidence work/dataset --output work/evaluation
```

Begin from a completed copy of `DATA_MANIFEST_TEMPLATE.csv`. The collector refuses blank permission metadata, resolves branches/tags to immutable commit SHAs and records the resolved source manifest. Source rights still require human verification; the command records the claim but cannot verify it.

The audit emits a file-level CSV and JSON summary, flags cross-author duplicates, and reports whether the folder meets the minimum training shape.

The evidence command stops if that audit gate fails. On success it runs the held-out benchmark, trains the selected fusion model, generates every presentation artifact and writes `evidence_manifest.json` with SHA-256 checksums for the complete evidence pack.

The training command refuses fewer than four authors or fewer than six eligible files per author. It removes exact duplicates globally, creates enrollment/query splits, constructs balanced same-author and different-author pairs, compares logistic fusion with the custom 5→16→8→1 neural head, selects by held-out-author F1 with Brier-score tie-breaking, calibrates the review/uncertain/consistent thresholds from the selected model's out-of-fold scores, trains that architecture on all pairs, and saves:

- `work/evaluation/results.json` — dataset counts, fold details and aggregate metrics;
- `codedna/artifacts/fusion_model.json` — scaler, weights, bias and thresholds.
- `work/evaluation/benchmark.svg` — presentation-ready three-system comparison;
- `work/evaluation/confusion_matrix.svg` — selected model's out-of-fold confusion counts;
- `work/evaluation/fold_metrics.csv` — held-out authors and selected-model metrics for every fold;
- `work/evaluation/EVIDENCE.md` — generated dataset, metric and threshold summary.
- `work/evaluation/evidence_manifest.json` — run metadata and checksums tying all evidence files together.

The chart and evidence document are generated from the same in-memory result that is written to `results.json`. Do not manually retype benchmark values into slides.

## Required reporting table

Populate this table from `results.json`; never enter aspirational values.

| System | ROC-AUC | F1 | Precision | Recall | False-positive rate |
|---|---:|---:|---:|---:|---:|
| AST-token representation only | 0.800 | 0.667 | 0.500 | 1.000 | 1.000 |
| Engineered signals only | 0.632 | 0.665 | 0.500 | 0.992 | 0.992 |
| Full CodeDNA fusion | 0.741 | 0.701 | 0.678 | 0.808 | 0.521 |

The table above uses a fixed 0.50 threshold for model comparison. The deployed three-way operating point uses a 0.9358 Consistent threshold and has a measured false-positive rate of **0.105**, recall of **0.329**, and uncertainty rate of **0.612**.

## Interpretation

The grouped split asks whether the fusion rule generalizes to developers excluded from fusion training. A held-out author's code is excluded from both the claimed-author and query-author side of every training pair. It does not prove generalization to institutions, languages, assignments or time periods absent from the dataset.

The current public benchmark contains four commit-pinned repository-owner proxy labels, 253 eligible files and no cross-author exact duplicates. Every source is recorded under an MIT license in `resolved_sources.csv`. Repository ownership is an imperfect authorship label because individual files may include outside contributions. The selected logistic fusion achieved held-out ROC-AUC 0.741 and F1 0.701 at the conventional 0.50 comparison threshold, where the false-positive rate is 0.521. The product uses a separately calibrated three-way policy: Review Recommended below 0.4605, Uncertain from 0.4605 to 0.9358, and Consistent at or above 0.9358. At that deployed Consistent threshold the held-out false-positive rate is 0.105, consistent-case recall is 0.329, and 61.2% of pairs abstain into Uncertain. This tradeoff is intentional and remains unsuitable for autonomous decisions.


