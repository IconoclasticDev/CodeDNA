# CodeDNA implementation status

## Completed — Milestone 1: runnable vertical slice

- Dependency-free Python service and browser UI.
- Lexical, AST-structural, and complexity feature extraction.
- Historical profile statistics and stability indicators.
- SHA-256 duplicate removal, Python validation, size/file caps, and invalid-file reporting.
- Consistency score, three-way verdict, Surface–Structure Gap, and ranked feature deviations.
- Profile creation, submission analysis, health, and deterministic demo API routes.
- Three-panel responsive interface with upload, progress, profile, report, warning, and limitation states.
- Consistent and Review Recommended demo fixtures produced by the real pipeline.
- Eleven automated tests covering feature extraction, validation, deduplication, profile creation, scoring, and demo separation.

## Completed — Milestone 2: hardened ingestion and trainable pipeline

- Safe in-memory ZIP ingestion with path, symlink, compressed-size, extracted-size, member-count and file-size controls.
- Allow-listed public GitHub collection through fixed GitHub hosts, with ZIP fallback messaging.
- Atomic local profile persistence across service restarts.
- Offline AST-token representation as a fourth active similarity signal.
- NumPy logistic fusion model with versioned JSON artifacts.
- Dataset loader, balanced pair construction, author-grouped folds, baselines and metric reporting.
- Model card, architecture, evaluation and demo documentation.
- Twenty-two passing automated tests, including live API integration coverage.

## Completed — Milestone 3: evaluation evidence layer

- Dataset audit command with invalid-file reporting and cross-author duplicate detection.
- Source/permission manifest template.
- Out-of-fold verdict-threshold calibration with an explicit uncertainty band.
- Fold variance and Brier score reporting alongside F1, ROC-AUC and false-positive rate.
- Active-model provenance API and visible report metadata.
- Downloadable evidence JSON from the report screen.
- One-command PowerShell launcher.
- Twenty-eight passing automated tests.

## Completed — Milestone 4: demo and evidence polish

- Up to four historical GitHub repositories per developer profile.
- Honest multi-step processing feedback for profile and submission requests.
- Visible analyzed/skipped/duplicate coverage in every report.
- Visible warnings alongside the evidence they qualify.
- Automatic benchmark SVG and evidence Markdown generation from real `results.json` values.
- Permission-aware public-repository collector with commit-SHA pinning and a resolved source manifest.
- Thirty passing automated tests.

## Completed — Milestone 5: optional CodeBERT integration

- Lazy optional CodeBERT runtime that preserves the dependency-free core.
- Function/class-aware chunking within the 512-token model limit.
- Attention-mask mean pooling, file-level aggregation and L2 normalization.
- Content-and-model-addressed embedding cache.
- Model downloads disabled unless explicitly enabled.
- Provider identity persisted in profiles and model artifacts.
- Hard rejection of incompatible profile, submission and fusion-model representations.
- Readiness reporting through the health and model APIs.
- Browser/API security headers and strict all-row repository URL validation.
- Custom 5→16→8→1 ReLU fusion head with dropout and L2 regularization.
- Held-out comparison against logistic fusion with F1/Brier model selection.
- Machine-readable readiness gates separating a working demo from Excellent-tier evaluation evidence.
- Generated out-of-fold confusion matrix and reviewer-friendly per-fold metrics CSV.
- One-command audited evidence build with SHA-256 artifact manifest.
- Standalone, print-ready HTML case report with score, components, deviations, coverage, warnings and interpretation boundary.
- Per-file consistency review map for multi-file submissions, ranked from lowest consistency and included in the standalone report.
- Deterministic mixed-file judge scenario demonstrating file-level triage through the real analysis pipeline.
- Direct public-GitHub link scanning fetches up to 100 eligible Python files from a commit-pinned tree without downloading the full repository archive.
- Forty-three passing automated tests, including a live large-repository scan and complete dataset-to-model artifact rehearsal.

## Completed — Milestone 9: error-controlled calibration

- Corrected the overlapping-distribution calibration so error-controlled tails expand the Uncertain band instead of forcing a narrow decision band.
- Deployed Consistent threshold increased to 0.9358; held-out false-positive rate decreased from 0.521 at the fixed comparison threshold to 0.105 at the deployed operating point.
- The tradeoff is explicit: consistent-case recall is 0.329 and 61.2% of held-out pairs abstain into Uncertain.
- Evidence UI now labels and displays the calibrated deployed false-positive rate.
- Confusion matrix and evidence manifest use the calibrated operating point while the comparison table retains the conventional 0.50 threshold.
- Hidden-browser verification completed the anomaly flow with zero JavaScript errors and four visible function heat-map rows.
- Forty-six automated tests pass.

## Completed — Milestone 8: function-level explainability

- Gate A stretch completed with a ranked function-level deviation heat map.
- Each function shows lexical, structural, and complexity deviation plus its strongest shifted feature.
- Function evidence is derived independently from the frozen fusion score and cannot change the verdict.
- The map appears in both the browser report and standalone downloadable HTML report.
- Forty-five passing automated tests cover the new API schema and ranking behaviour.
- Gate B remains closed until grouped evaluation contains at least six author labels.

## Completed — Milestone 7: multi-page product flow

- Focused landing page with clear Analyze and Evidence routes.
- Dedicated analysis workspace containing only profile, fingerprint and report steps.
- Dedicated competition evidence and methodology page.
- Deterministic 1.6-second demo handoff keeps the fingerprint readable before opening the report.
- Completed workflow steps remain directly navigable after a report is generated.
- Submission drag-and-drop now targets the visible drop zone correctly.
- Forty-four passing automated tests.
## Completed — Milestone 6: evidence freeze

- Optional CodeBERT dependencies and `microsoft/codebert-base` weights installed and locally validated at 768 normalized dimensions.
- Seven public MIT-licensed repositories pinned to immutable commit SHAs across four repository-owner proxy labels.
- Dataset audit: 253 eligible files and zero cross-author exact-duplicate hashes.
- Leakage-free grouped evaluation excludes each held-out author's code from both sides of every training pair.
- Logistic fusion selected over the MLP challenger and activated with calibrated three-way thresholds.
- Fixed-threshold held-out results: ROC-AUC 0.741, F1 0.701, precision 0.678, recall 0.808 and false-positive rate 0.521.
- Corrected three-way calibration reduces the deployed impostor-consistent rate to 0.105 by routing 61.2% of overlapping cases to Uncertain; strict-threshold recall is 0.329.
- Readiness gate now requires source-manifest permission/license metadata in addition to dataset shape.

## Release limitations

- The active benchmark uses repository-owner proxy labels; ownership does not guarantee every file has one author.
- The deployed false-positive rate is 0.105, but 61.2% uncertainty and 0.329 strict-threshold recall are too weak for autonomous or disciplinary use.
- The active trained artifact uses the AST-token representation. CodeBERT is locally available but requires a separate full benchmark before replacing it.
- The product remains Python-only and treats historical code as one distribution without temporal adaptation.
- Every result is review support; it does not establish AI use, plagiarism or misconduct.

## Post-hackathon validation

1. Replace proxy labels with consented, file-attributed longitudinal author histories.
2. Expand beyond four authors and report confidence intervals and subgroup results.
3. Benchmark the cached CodeBERT representation against the active AST-token system.
4. Reduce false positives before any institutional pilot.



