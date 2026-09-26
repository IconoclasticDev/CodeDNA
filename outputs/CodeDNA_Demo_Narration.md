# CodeDNA submission demo narration

## 1 — Problem and product
Every developer leaves recurring habits in code: naming, structure, complexity, and problem-solving patterns. Code D N A turns those habits into reviewable evidence. It compares a new Python submission with the developer's own history and highlights unexplained changes. It does not claim to detect A I, prove authorship, or make disciplinary decisions.

## 2 — Fast, safe enrollment
Enrollment starts with real historical work. A reviewer can select Python files, upload a bounded ZIP archive, or paste up to four public GitHub repository links. The scanner validates each GitHub URL, pins the resolved commit, reads only eligible Python files, removes exact duplicates, and reports skipped or malformed inputs instead of failing silently.

## 3 — Behavioral fingerprint
From at least ten distinct files, Code D N A builds a behavioral fingerprint. It summarizes lexical habits such as naming, comments, and type hints; A S T structure such as control flow and nesting; complexity patterns; and a privacy-preserving local code representation. The profile shows file, function, and line coverage, along with stability for each signal family.

## 4 — Submission review
A new submission passes through the same pipeline. The selected logistic fusion model combines five inputs after being compared with a custom neural challenger. The report returns a zero-to-one-hundred consistency score and one of three verdicts: Consistent, Uncertain, or Review Recommended. It also exposes every component score, the surface-versus-structure gap, coverage, warnings, and the largest measurable deviations.

## 5 — Explainability that guides review
Reviewers can immediately see where a shift concentrates. Multi-file submissions are ranked from lowest consistency, while the function-level heat map separates lexical, structural, and complexity deviation for every function. Here, classify is the first function to inspect. These explanations guide human review and never modify the trained verdict.

## 6 — Measured evidence
The Evidence page separates a working demo from scientific claims. The current leakage-aware evaluation holds each author out of both sides of training pairs, using two hundred forty-seven distinct files across four commit-pinned repository-owner proxy labels. The selected model records a held-out R O C A U C of point seven four one and F one of point seven zero one. Error-controlled calibration lowers the deployed false-positive rate to point one zero five by routing overlapping cases to Uncertain. The tradeoff is explicit: strict recall is point three two nine, and sixty-one point two percent of held-out pairs abstain into Uncertain.

## 7 — Deliverable and boundary
Every result can be downloaded as evidence JSON or a standalone, print-ready HTML review report containing derived evidence and no submitted source code. Code D N A is Python-only, its current labels are proxy labels, and the benchmark remains prototype-scale. Its purpose is to focus a fair conversation: show what changed, show how confident the system is, and keep the final decision with a human reviewer.
