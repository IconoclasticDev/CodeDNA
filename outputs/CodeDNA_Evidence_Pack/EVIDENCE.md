# CodeDNA evaluation evidence

This file is generated from the machine-readable evaluation result.

- Authors: **4**
- Files: **247**
- Balanced profile/query pairs: **152**
- Protocol: **grouped by claimed author**
- Selected fusion: **full_fusion_logistic**

| System | ROC-AUC | F1 | F1 std | Precision | Recall | False-positive rate | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| AST-token only | 0.800 | 0.667 | 0.000 | 0.500 | 1.000 | 1.000 | 0.313 |
| Engineered signals | 0.632 | 0.665 | 0.003 | 0.500 | 0.992 | 0.992 | 0.314 |
| CodeDNA fusion | 0.741 | 0.701 | 0.041 | 0.677 | 0.808 | 0.521 | 0.261 |

## Calibrated three-way verdict

- Review Recommended below **0.461**
- Uncertain from **0.461** to **0.936**
- Consistent at or above **0.936**
- Observed false-review rate: **0.092**
- Observed impostor-consistent rate: **0.105**
- Overall uncertain rate: **0.612**

The comparison table uses the conventional fixed 0.50 threshold. The rates above describe the deployed three-way operating point, where ambiguous cases abstain into **Uncertain**.

> Prototype-scale evaluation; broader longitudinal validation is required before institutional use.
