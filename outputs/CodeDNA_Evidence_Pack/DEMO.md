# Five-minute CodeDNA demo

1. Open `http://127.0.0.1:8000/analyze.html` and state: “CodeDNA measures consistency with a developer's own history; it does not claim to detect AI.”
2. Show that profiles can be created from local Python files, a bounded ZIP or a public GitHub repository.
3. Run **Familiar-style demo** and point out its higher, agreeing component signals. If the calibrated model returns Uncertain, explain that the system preserves uncertainty instead of forcing a reassuring verdict.
4. Run **Anomaly demo** and point out the lower structural and complexity scores, the Surface–Structure Gap, and the function-level heat map. Open with the highest-ranked function and explain that its three heat cells prioritize human review without changing the model score.
   Run **Multi-file demo** and use the file-level review map to show where the deviation concentrates without turning a single file into a misconduct claim.
5. Open `http://127.0.0.1:8000/evidence.html`, then show the evaluation result produced from the real author dataset. State the author/file/pair counts, held-out-author protocol, F1 and false-positive rate.
6. Close with the limitation notice and human-review requirement.

Download the standalone review report to show that the evidence can be inspected or printed without the live application. It contains derived evidence and no submitted source code.

If GitHub or model infrastructure is unavailable, use the built-in demos. They are deterministic fixtures passed through the real extraction and scoring pipeline, not hard-coded report JSON.



The fingerprint and review report are separate workflow pages inside the analyzer. When using a prepared demo, allow the visible fingerprint pause to finish; the review report opens automatically. For a real submission, the report is generated only after files are added and **Analyze consistency** is selected.
