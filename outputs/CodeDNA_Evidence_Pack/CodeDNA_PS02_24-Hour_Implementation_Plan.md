# CodeDNA — 24-Hour Implementation Plan

## PS #02: Code Authenticity Checker for Student Submissions

**Objective:** Build the strongest credible hackathon version of a developer-behaviour fingerprinting system in 24 hours, with evidence aimed at the **Excellent** band in Innovation, AI Implementation, Functionality, UI/UX, and Documentation.

**Product claim:**

> CodeDNA learns a developer's historical coding behaviour and measures whether a new submission is consistent with that history. It provides review evidence; it does not claim to prove AI use or misconduct.

This distinction is central to the product. A global “AI-generated code detector” is easy to challenge. Personalized behavioural authentication is a clearer and more defensible machine-learning problem.

---

## 1. Success target and scoring strategy

The goal is to cross the lower boundary of Excellent in every category with working, visible evidence. Do not spend scarce hours maximizing one category after its Excellent evidence is secure.

| Rubric category | Excellent band | 24-hour target | Evidence shown to judges |
|---|---:|---:|---|
| Innovation & Originality | 16–20 | 17–18 | Personalized behavioural authentication; Surface–Structure Consistency Gap; evidence-first three-way verdict |
| AI Implementation | 23–30 | 24–26 | Frozen CodeBERT backbone, engineered source-code signals, trained fusion head, author-grouped evaluation, ablation table |
| Functionality | 19–25 | 21–23 | End-to-end repo/ZIP workflow, narrow supported envelope, clear failures, deterministic demo fixtures, meaningful tests |
| UI/UX | 12–15 | 13–14 | Three polished screens, progress feedback, readable visual hierarchy, actionable explanations, responsive states |
| Documentation | 8–10 | 8–9 | Architecture, setup, API contract, model card, limitations, evaluation protocol, demo guide |
| **Expected total** |  | **83–89** | All five categories have concrete Excellent-tier evidence |

The score is not guaranteed; judges decide it. This plan maximizes the probability that every claim can be demonstrated rather than merely described.

---

## 2. Frozen scope

### 2.1 The exact end-to-end user journey

1. The reviewer enters one or more public GitHub repository URLs for a student, or uploads historical code as a ZIP.
2. CodeDNA validates the inputs, filters eligible Python files, removes duplicates and generated/vendor content, and builds a historical profile.
3. The reviewer sees the student's Code DNA: profile statistics, feature stability, and a visual fingerprint.
4. The reviewer uploads a new Python submission as a `.py` file or ZIP.
5. CodeDNA applies the same feature pipeline and returns:
   - an authorship-consistency score from 0–100;
   - a three-way verdict: **Consistent**, **Uncertain**, or **Review Recommended**;
   - component similarities for lexical style, AST structure, complexity, and semantic representation;
   - the Surface–Structure Consistency Gap;
   - the largest measurable deviations from the historical profile;
   - a plain-language limitation notice.

### 2.2 Supported production envelope

The hackathon build supports:

- Python source code only;
- public GitHub repository URLs;
- multiple historical repositories per profile;
- historical ZIP uploads as a fallback;
- new submissions as one `.py` file or a ZIP;
- a minimum of 10 valid historical files, with a warning below 20;
- repositories capped at 100 eligible files and 50 MB of downloaded source;
- local inference after the embedding model has been downloaded;
- one profile analysis at a time per worker.

### 2.3 Explicitly outside the 24-hour scope

- private repository authentication;
- languages other than Python;
- fine-tuning CodeBERT;
- contrastive training over a large author corpus;
- control-flow graphs, program-dependency graphs, or graph neural networks;
- temporal/LSTM modelling of style evolution;
- a generic AI-code classifier;
- plagiarism matching against external corpora;
- browser extensions, LMS integrations, user accounts, billing, or production deployment hardening;
- definitive statements about AI usage, cheating, or authorship.

These exclusions keep the build testable and prevent unfinished features from weakening the demo.

### 2.4 Scope-lock rule

No stretch feature begins until all of the following are true:

- the golden-path flow works from clean start to final report;
- the trained fusion model is connected to the application;
- the evaluation script produces real metrics;
- the five must-pass failure states work;
- the demo fixtures can run without network access;
- the README and limitations are present;
- the team has completed one timed rehearsal.

---

## 3. Additions beyond the lean MVP

The lean MVP is: feature extraction, a frozen embedding model, hand-written similarity weights, and a simple result page. The following additions are the smallest upgrades that materially improve rubric performance.

| Addition | What is implemented | Why it earns rubric points | Cost cap |
|---|---|---|---:|
| **Consistency Fusion Head (CFH)** | A small trained MLP or logistic model that fuses four similarity signals and one interaction feature | Creates a genuine trainable ML component and supports a custom-architecture claim | 3 hours including evaluation |
| **Surface–Structure Consistency Gap (SSCG)** | Measures disagreement between surface style and deeper structure/complexity/semantic behaviour | Supplies a project-specific idea and a compelling explanation for style imitation | 45 minutes |
| **Author-grouped evaluation** | Held-out authors using GroupKFold or Leave-One-Author-Out | Shows generalization to unseen developers and prevents pair/file leakage | 1 hour |
| **Three-model ablation** | Compare CodeBERT-only, engineered-features-only, and full fusion | Provides clear benchmarking required by the AI rubric | 45 minutes after features exist |
| **Calibrated three-way verdict** | Consistent / Uncertain / Review Recommended using validation thresholds | Avoids unjustified binary accusations and exposes uncertainty | 45 minutes |
| **Feature-level explanations** | Historical mean, submission value, z-score, and direction for top deviations | Makes the output actionable and visibly explainable without an LLM | 1.5 hours |
| **Narrow hardening envelope** | Validation, caps, filtering, deduplication, syntax-error recovery, useful error states | Moves functionality from a fragile demo toward a reliable product slice | 2 hours |
| **Offline demo fixtures** | Cached profiles, embeddings, and two known submissions | Protects the live demo from GitHub/network/model-download failures | 45 minutes |
| **Model card and experiment report** | Data, split, metrics, limitations, intended use, prohibited interpretation | Raises documentation quality and scientific credibility | 1 hour |

Do not add Git-history analysis, multi-language support, an LLM explanation layer, or fine-tuning unless the stretch gates in Section 16 are met.

---

## 4. Architecture

```text
Historical GitHub URLs / ZIP
              │
              ▼
     Input validation + safe ingest
              │
              ▼
  Python filter → deduplicate → caps
              │
              ▼
┌──────────────────────────────────────────┐
│ Shared feature pipeline                  │
│                                          │
│  Lexical     AST       Complexity        │
│  features    features  metrics           │
│       └─────────┬──────────┘              │
│                 ├────────── CodeBERT      │
│                 │            chunks       │
└─────────────────┼────────────────────────┘
                  ▼
      Historical developer profile
      means, variance, centroids, stability
                  │
New submission ───┤
                  ▼
     Same shared feature pipeline
                  │
                  ▼
     Similarity vector + SSCG feature
                  │
                  ▼
      Trained Consistency Fusion Head
                  │
          ┌───────┼────────┐
          ▼       ▼        ▼
       score   verdict  explanations
                  │
                  ▼
          Submission Report UI
```

### 4.1 Suggested implementation stack

- **Frontend:** React + Vite, Tailwind CSS, Recharts.
- **Backend:** FastAPI + Pydantic.
- **Analysis:** Python `ast`, `tokenize`, Radon, NumPy, pandas.
- **Embeddings:** `microsoft/codebert-base` through Hugging Face Transformers, frozen.
- **Model:** scikit-learn logistic regression as the reliability-first default; switch to a tiny PyTorch MLP only if the data and metrics justify it.
- **Persistence:** local JSON/Parquet artifacts and model files. SQLite is optional, not required.
- **Tests:** pytest for extractors, validation, scoring, and API behaviour.

Logistic regression is acceptable as a trained fusion head and is safer on a small dataset. A tiny MLP provides a stronger architecture story but has more variance and debugging risk. Train both quickly if possible, then ship the one with the better held-out result.

### 4.2 Minimal backend modules

```text
backend/
  app.py                  # FastAPI routes and health status
  schemas.py              # request/response contracts
  ingest.py               # URL/ZIP validation, clone/download, limits
  filters.py              # exclusions, language filter, SHA dedupe
  features/
    lexical.py
    structural.py
    complexity.py
    semantic.py
  profile.py              # developer centroid, variance, stability
  scoring.py              # similarities, SSCG, thresholds
  explain.py              # deterministic deviation messages
  model.py                # load and run trained fusion model
  artifacts/              # model, scaler, threshold config
```

### 4.3 Minimal API contract

| Route | Purpose | Required response behaviour |
|---|---|---|
| `GET /health` | Dependency/model readiness | Return model, embedding, and API readiness independently |
| `POST /profiles` | Build profile from URLs or ZIP | Return job/profile ID and validated input summary |
| `GET /profiles/{id}` | Read profile | Return counts, fingerprint, stability, warnings |
| `POST /profiles/{id}/analyze` | Analyze submission | Return score, verdict, component scores, deviations, warnings |
| `GET /demo/{case}` | Load cached demo case | Return deterministic authentic or anomaly report |

The frontend should treat error responses as designed product states, not raw stack traces.

---

## 5. ML and feature pipeline

### 5.1 Eligible source selection

Include `.py` files and exclude paths containing:

```text
.git, .venv, venv, env, site-packages, node_modules,
vendor, dist, build, generated, migrations, __pycache__,
coverage, fixtures, third_party
```

Also exclude minified/generated-looking files, files larger than 1 MB, exact SHA-256 duplicates, and files with fewer than five meaningful lines. Record every exclusion count for transparency.

### 5.2 Lexical/style features

Use approximately 12 stable normalized signals:

- snake_case identifier ratio;
- camelCase identifier ratio;
- average and standard deviation of identifier length;
- identifier vocabulary diversity;
- comment density;
- docstring density;
- type-hint frequency;
- blank-line density;
- average parameters per function;
- imports per 100 LOC;
- average function length;
- string-literal and numeric-literal density.

Use Python tokenization or AST nodes instead of fragile regular expressions wherever possible.

### 5.3 AST structural features

Use approximately 12 normalized signals:

- `if`, `for`, `while`, `try`, `with`, and `match` frequency;
- function and class density;
- lambda frequency;
- comprehension frequency;
- return and call density;
- mean and maximum AST depth;
- approximate nesting depth;
- async function frequency.

Normalize count features per 100 AST nodes or per function so file size does not dominate similarity.

### 5.4 Complexity features

Use five to seven signals:

- mean and maximum cyclomatic complexity;
- maintainability index;
- logical LOC;
- mean function complexity;
- complexity dispersion;
- proportion of functions above complexity 10.

If Radon fails on a file, skip only that file's complexity contribution and preserve the other feature groups.

### 5.5 Semantic embeddings

Use a frozen CodeBERT model. Never truncate an entire large file to its first 512 tokens. Split at function and class boundaries, tokenize each chunk to the model limit, embed each chunk, and mean-pool the chunk embeddings into a file vector. Mean-pool eligible historical file vectors to create the author's semantic centroid.

Cache embeddings by file hash. This prevents repeated demo runs from paying the embedding cost again.

### 5.6 Historical profile

For each scalar feature, store:

- mean;
- standard deviation with an epsilon floor;
- median and interquartile range for display;
- sample count;
- stability score based on normalized dispersion.

For grouped vectors, store:

- standardized author centroid;
- covariance only if it is numerically stable;
- otherwise cosine similarity to the centroid.

Do not force Mahalanobis distance with more features than historical samples. If covariance is singular or unstable, use shrinkage covariance or cosine/standardized Euclidean distance.

### 5.7 Fusion inputs

For a claimed-author profile and a submission, calculate:

```text
S_lexical    = similarity of lexical feature vectors
S_ast        = similarity of normalized AST vectors
S_complexity = similarity of complexity vectors
S_semantic   = cosine similarity to CodeBERT centroid
G_sscg       = S_lexical - mean(S_ast, S_complexity, S_semantic)
```

Scale similarities to `[0, 1]`. The fusion input is:

```text
x = [S_lexical, S_ast, S_complexity, S_semantic, G_sscg]
```

### 5.8 Consistency Fusion Head

Reliability-first model:

```text
StandardScaler → LogisticRegression(class_weight="balanced") → probability
```

Optional tiny MLP challenger:

```text
5 inputs → Linear(16) → ReLU → Dropout(0.15)
         → Linear(8)  → ReLU → Linear(1) → Sigmoid
```

Select the model by held-out author F1 and false-positive rate, not by narrative appeal. Save the scaler, model, threshold configuration, feature schema version, and training metadata together.

### 5.9 Verdicts and threshold calibration

Start with provisional bands:

```text
p >= 0.70          Consistent
0.40 <= p < 0.70  Uncertain
p < 0.40           Review Recommended
```

Then calibrate on validation predictions. Optimize for a low false-positive rate because falsely flagging an authentic submission is the most harmful failure. Freeze the thresholds before testing the demo cases and record how they were selected.

Every report must display:

> A low consistency score indicates behavioural deviation from the supplied history. It does not establish AI use, plagiarism, or misconduct. A human reviewer must interpret the evidence.

---

## 6. Dataset and evaluation design

### 6.1 Data target

Collect a small real dataset within a strict two-hour cap:

- 6–8 authors;
- 20–40 valid Python files per author;
- approximately 150–250 files total;
- repositories with reasonably attributable authorship;
- public repositories or code supplied with permission.

Create a simple manifest:

```text
author_id, repository, commit_or_snapshot, license_or_permission,
eligible_files, excluded_files, collection_notes
```

Do not mix tutorial templates, forks, copied coursework, or generated/vendor code into author profiles. If authorship is unclear, exclude the repository.

### 6.2 Pair construction

For each author:

- split that author's files into enrollment/history files and query files;
- build the profile from enrollment files only;
- pair the profile with held-out same-author queries as positive examples;
- pair the profile with other-author queries as negative/impostor examples;
- balance positive and negative pairs, or use class weighting.

Never allow a query file to contribute to the profile against which it is evaluated.

### 6.3 Leakage-safe split

The outer evaluation split is by **claimed author**, using GroupKFold or Leave-One-Author-Out. All pairs involving a held-out claimed author remain outside training. If authors are too few for a stable four-fold result, report Leave-One-Author-Out mean and per-fold variance.

Where repository templates or shared coursework exist, group by repository/template family too, or remove them. Hash-based deduplication must run before splitting.

### 6.4 Required benchmark table

Generate real values only:

| System | ROC-AUC | F1 | Precision | Recall | False-positive rate |
|---|---:|---:|---:|---:|---:|
| CodeBERT cosine only | actual | actual | actual | actual | actual |
| Engineered signals only | actual | actual | actual | actual | actual |
| **Full CodeDNA fusion** | **actual** | **actual** | **actual** | **actual** | **actual** |

Also show the confusion matrix for the chosen operating threshold. If the fusion model does not win, report that honestly and ship the best validated scorer while retaining the fusion experiment as evidence of technical work.

### 6.5 Minimum credible evaluation outputs

- author-grouped fold definition;
- total authors, files, profiles, positive pairs, and negative pairs;
- F1, precision, recall, ROC-AUC, and false-positive rate;
- mean and standard deviation across folds;
- confusion matrix;
- three-system ablation;
- one known limitation caused by the small sample;
- a machine-readable results file and one presentation-ready chart.

### 6.6 Optional adversarial mini-test

Only after the required evaluation is complete, create three style-imitation examples using a consenting teammate's history. Compare ordinary other-author code with code deliberately reformatted to imitate lexical habits. This is a qualitative stress test, not a replacement for the held-out benchmark. It exists to illustrate whether SSCG reacts when surface style looks similar but deeper signals differ.

---

## 7. Explainability design

Explanations are calculated from real feature differences, not generated by an LLM.

For each scalar feature:

```text
z = (submission_value - historical_mean) / max(historical_std, epsilon)
```

Rank by absolute z-score and show the top three to five deviations. Example:

```text
Type annotations
Historical mean: 3.2%
Submission:      91.7%
Deviation:       +4.6σ

Average function size
Historical mean: 19.2 lines
Submission:       7.1 lines
Deviation:       -3.2σ
```

Use neutral language:

- “appears much more frequently than in the supplied history”;
- “falls outside the profile's usual range”;
- “surface naming is similar while structural behaviour differs.”

Avoid “AI-written,” “cheating detected,” or “fraudulent.”

---

## 8. UI plan

Build only three primary screens and a compact About/Method drawer.

### Screen 1 — Create Developer Profile

Required elements:

- product statement in one sentence;
- repeatable GitHub URL input;
- ZIP fallback;
- explicit “Python supported” label;
- privacy/usage note;
- input validation before submission;
- progress steps:
  1. validating sources;
  2. collecting files;
  3. filtering and parsing;
  4. extracting behaviour signals;
  5. generating embeddings;
  6. building profile;
- live counts for accepted, excluded, duplicate, and invalid files;
- clear recovery action for each failure.

### Screen 2 — Developer Fingerprint

Required elements:

- files, repositories, functions, and valid-sample counts;
- profile-confidence indicator based on sample count and stability;
- six-axis radar or compact bar visualization:
  - naming behaviour;
  - documentation habits;
  - control-flow structure;
  - complexity;
  - modularity;
  - semantic representation;
- three most stable characteristics;
- warnings for weak or heterogeneous histories;
- prominent “Analyze submission” action.

Do not label profile stability as “authenticity.” It describes the baseline quality, not the student.

### Screen 3 — Submission Report

Information order:

1. authorship-consistency score;
2. three-way verdict and uncertainty wording;
3. four component similarity bars;
4. SSCG callout when it crosses its validation threshold;
5. top feature deviations with historical vs submission values;
6. analysis coverage: files analyzed, files skipped, warnings;
7. limitations and human-review notice;
8. export JSON/report action only if core work is complete.

Example hero state:

```text
AUTHORSHIP CONSISTENCY                         34 / 100
REVIEW RECOMMENDED

Lexical style        89%
AST structure        52%
Complexity           41%
Semantic behaviour   56%

Surface–Structure Gap: +39 points
Surface naming resembles the history, while deeper program
structure and complexity differ. Review the deviations below.
```

### Essential UX states

- empty;
- validating;
- processing with meaningful progress;
- success;
- partial success with skipped-file warning;
- insufficient history;
- unsupported content;
- repository unavailable;
- model unavailable;
- unexpected failure with a retry action.

Accessibility minimums: keyboard navigation, visible focus, semantic labels, contrast-compliant colors, icons plus text for verdicts, and no information conveyed by color alone.

---

## 9. Edge cases and expected behaviour

| Edge case | Product behaviour | Must be tested? |
|---|---|---:|
| Malformed GitHub URL | Reject before processing with an example of a valid URL | Yes |
| Private or inaccessible repository | Explain access limitation and offer ZIP upload | Yes |
| URL points outside allowed Git host/path form | Reject; never pass arbitrary URL text to a shell | Yes |
| No Python files | Unsupported-content state | Yes |
| Fewer than 10 historical files | Block scoring; show insufficient-profile guidance | Yes |
| 10–19 historical files | Allow with low-confidence warning | Yes |
| Syntax-invalid Python file | Skip file, preserve count and filename-safe reason | Yes |
| Mixed-language repository | Analyze Python only and show coverage | Yes |
| Duplicate files | Deduplicate by content hash and report count | Yes |
| Generated/vendor/environment files | Exclude through path and content rules | Yes |
| Huge file | Chunk functions/classes; cap size and warn if excluded | Yes |
| Huge repository | Apply count/size caps and report truncation | Yes |
| Empty or malformed ZIP | Clear validation error | Yes |
| Path traversal in ZIP | Reject unsafe members before extraction | Yes |
| Binary disguised as `.py` | Reject decoding/parsing failure safely | Yes |
| Zero-variance historical feature | Apply epsilon floor and suppress misleading z-score | Yes |
| CodeBERT unavailable | Show dependency state; allow cached demo | Yes |
| GitHub rate limit/network outage | Use ZIP or cached demonstration | Demo rehearsal |
| Mixed authorship in history | Warn that profile quality depends on attributable history | Documentation |

Security basics within scope: clone without executing repository code, never import analyzed files, disable symlink traversal, validate ZIP paths, limit file count/size/time, redact local paths from user-facing errors, and delete temporary working directories after analysis.

---

## 10. Team execution model

The board below assumes four people. Each workstream has one owner, but integration contracts are agreed in Hour 0–1.

| Owner | Primary responsibility | Required handoff |
|---|---|---|
| **A — Backend/Ingestion** | API, safe repo/ZIP ingest, filtering, profiles, error states | Stable JSON fixtures and routes for frontend |
| **B — ML/Evaluation** | dataset manifest, pair creation, fusion models, grouped evaluation, model artifacts | Versioned model, scaler, thresholds, metrics JSON |
| **C — Features/Quality** | lexical, AST, complexity, semantic extraction, caching, tests | Stable feature schema and extractor contract |
| **D — Frontend/Product** | three screens, charts, progress/error states, demo flow, visual polish | UI integrated first with fixtures, then live API |

Shared responsibilities:

- A and C agree on the file-analysis object in Hour 1.
- B and C freeze the five fusion inputs by Hour 6.
- A and D freeze API response examples by Hour 2.
- All owners stop isolated feature work at Hour 12 and prioritize integration.
- One person other than the feature author runs each demo path.

### If the team has three people

- Person 1: ingestion + backend;
- Person 2: features + ML/evaluation;
- Person 3: frontend + documentation/demo.

Use logistic regression only, omit the optional MLP, and begin from cached CodeBERT embeddings if time becomes tight.

### If the team has five or six people

Add one dedicated quality/integration owner and, if available, one documentation/demo owner. Do not expand core product scope. Extra capacity goes to tests, accessibility, experiment reproducibility, fixture quality, and rehearsal. Stretch work still requires the gates in Section 16.

### Working rules

- One main branch must stay runnable; use short-lived feature branches.
- Every route and model output has a checked-in example payload.
- Commit at least every 60–90 minutes with small, reversible changes.
- Integrate at Hours 6, 10, 14, and 18.
- At Hour 18, freeze features. After that, only bug fixes, copy, performance, evidence, and demo hardening are allowed.

---

## 11. Hour-by-hour plan

### Hour 0–1 — Lock contracts and demo truth

**All:** Confirm product claim, frozen scope, supported envelope, owners, repository structure, and one authentic/one anomalous demo case.

**Deliverables:** architecture sketch, response JSON examples, feature schema draft, definition of done, shared task board.

**Exit gate:** everyone can describe the same end-to-end flow in 30 seconds.

### Hour 1–2 — Build skeletons and start data collection

- A: create backend, health route, request schemas, fixture responses.
- B: create author/repository manifest and start collecting consented/public data.
- C: implement file filters, SHA dedupe, safe parsing contract.
- D: create routes/layout/design tokens and all three screen skeletons.

**Exit gate:** frontend renders fixture data; backend returns matching payloads.

### Hour 2–4 — First vertical slice

- A: public-repo/ZIP ingestion with caps and exclusions.
- B: finish 6–8-author dataset or stop at two-hour cap; build pair/split script.
- C: lexical + AST extractors with normalized outputs.
- D: profile input and progress/error states; fingerprint/report fixture screens.

**Exit gate:** local historical ZIP produces a profile object without embeddings.

### Hour 4–6 — Complete analysis signals

- A: profile storage and submission-analysis route.
- B: data audit, leakage checks, grouped folds, baseline notebook/script.
- C: Radon complexity, CodeBERT chunking, hash cache.
- D: component bars, radar/bar fingerprint, top-deviation component.

**Exit gate:** one file passes all four signal extractors; UI can display its fixture report.

### Hour 6–8 — Connect baseline scoring

- A/C: historical means/variance/centroids, submission similarities, deterministic explanations.
- B: generate pair features and train CodeBERT-only and engineered baselines.
- D: connect live profile route while retaining fixture mode.

**Exit gate:** live pipeline returns four similarities and ranked deviations.

### Hour 8–10 — Train and evaluate fusion

- B: calculate SSCG, train logistic fusion and optional MLP, run grouped evaluation.
- C: address extraction failures exposed by the dataset.
- A: load versioned scaler/model/config and return fusion score.
- D: build score/verdict/SSCG states and methodology drawer.

**Exit gate:** saved model produces repeatable predictions; initial real metrics exist.

### Hour 10–12 — End-to-end integration

- Connect profile creation, submission upload, scoring, explanations, and UI.
- Create deterministic cached demo profiles and reports.
- Add loading, partial-success, and failure-state plumbing.

**Exit gate:** golden path succeeds twice from a clean application start.

### Hour 12–14 — Functionality hardening

- Exercise invalid URL, no Python, too few files, syntax error, duplicate, huge file, empty ZIP, and model-down cases.
- Implement ZIP path-traversal protection and time/size limits.
- Fix raw exceptions and expose actionable messages.

**Exit gate:** the five must-pass failure states work: invalid source, inaccessible repo, no Python, insufficient history, malformed submission.

### Hour 14–16 — Evaluation and evidence freeze

- Rerun the final author-grouped benchmark using frozen features.
- Generate metrics JSON, ablation chart, fold summary, and confusion matrix.
- Calibrate thresholds using validation predictions.
- Record dataset and limitations.

**Exit gate:** every number in the pitch traces to an artifact; no fabricated metrics.

### Hour 16–18 — UI polish and test pass

- Responsive layout, keyboard/focus check, color/label review.
- Add coverage counts, warnings, method details, and limitation notice.
- Run targeted automated tests and fix failures.
- Optimize obvious latency with cached embeddings.

**Exit gate:** a new teammate can use the product without instructions.

### Hour 18–20 — Documentation and deployment package

- Freeze features.
- Write README, setup, architecture, API examples, model card, evaluation notes, and troubleshooting.
- Prepare one-command local start or a simple launcher.
- Verify offline cached-demo mode.

**Exit gate:** fresh-start setup succeeds on one teammate's machine.

### Hour 20–22 — Rehearsal and failure injection

- Run the complete five-minute demo three times.
- Deliberately disable network/model service and exercise fallback.
- Ask hostile judge questions and tighten answers.
- Fix only demo-blocking issues.

**Exit gate:** median demo time is under five minutes and cached fallback takes under 30 seconds to activate.

### Hour 22–23 — Evidence pack

- Final screenshots and short backup recording.
- Freeze benchmark slide and architecture diagram.
- Confirm authorship/permission manifest and limitations.
- Tag the demo build and back up model/config/fixtures.

### Hour 23–24 — Buffer and final rehearsal

- No new features.
- Clean restart, smoke test, timed rehearsal, device/power/network check.
- Assign speaking roles and Q&A ownership.

**Final exit gate:** live path, cached path, slides, model artifacts, and repository are all independently available.

---

## 12. Definition of done

### Product

- Profile can be built from at least one supported input type.
- Submission can be analyzed against that profile.
- Score, verdict, four component scores, SSCG, and top deviations are visible.
- Insufficient data and partial analysis are clearly distinguished from a low score.
- Cached authentic and anomaly demos work without internet.

### ML

- Fusion model is actually trained and versioned.
- Evaluation holds out claimed authors.
- No exact duplicate crosses a data split.
- Baselines and full model are compared with real numbers.
- Threshold selection and false-positive rate are reported.

### Quality

- At least 15 meaningful automated tests pass.
- No analyzed repository code is executed.
- ZIP traversal, size caps, duplicate files, syntax errors, and empty content are handled.
- User-facing failures contain recovery steps.

### UX and documentation

- All three screens are responsive and keyboard-usable.
- Progress and warning states are visible.
- README covers setup, architecture, method, evaluation, limitations, and demo.
- The report carries the human-review notice.

---

## 13. Test plan

Write a small set of meaningful tests rather than chasing coverage percentage.

### Unit tests

- naming ratios and comment density on known snippets;
- AST counts and depth on known snippets;
- syntax-error recovery;
- feature normalization and zero-variance behaviour;
- SSCG calculation;
- score bounds and verdict boundaries;
- deterministic ranking of deviations;
- SHA-based deduplication;
- excluded-directory filtering;
- safe ZIP member validation.

### API/integration tests

- invalid repository URL;
- empty ZIP;
- no eligible Python;
- insufficient historical files;
- partial success with invalid files;
- profile then analyze golden path;
- missing model artifact and health status;
- cached demo response.

### Manual acceptance tests

- valid public repository;
- network outage fallback;
- large function chunking;
- mixed-language ZIP;
- keyboard-only journey;
- mobile-width report;
- clean restart on the presentation machine.

---

## 14. Risk controls

| Risk | Early warning | Control | Fallback |
|---|---|---|---|
| CodeBERT download/inference is slow | No embedding by Hour 5 | Download/cache immediately; hash-cache results; batch chunks | Use precomputed embeddings in demo; keep live engineered signals |
| Dataset takes too long | Fewer than 5 usable authors at Hour 3 | Stop collection at two hours; use fewer authors and LOAO evaluation | Report small-sample limitation honestly |
| Fusion model performs poorly | Worse than baseline at Hour 10 | Check leakage, scaling, imbalance, and label construction once | Ship best validated scorer; show fusion experiment honestly |
| Too few samples for covariance | Singular/unstable matrix | Use shrinkage or cosine/standardized Euclidean | Remove Mahalanobis claim |
| GitHub is unavailable/rate-limited | Clone fails during rehearsal | ZIP route, cached profiles, local fixtures | Run cached demo and explain live ingestion separately |
| Frontend/backend integration slips | Fixture/live schemas differ at Hour 8 | Freeze example payloads at Hour 2 | Demo fixture endpoint with real precomputed outputs |
| Repository contains unsafe content | Archives/links escape workspace | Never execute code; validate paths and symlinks; apply caps | Reject unsafe input with clear message |
| False accusations undermine trust | Binary “AI” wording appears | Three-way verdict, uncertainty, evidence, human-review notice | Remove generic AI claim from pitch entirely |
| Team expands scope | New feature proposed before Hour 18 | Scope-lock checklist and single product owner | Put idea in stretch backlog |
| Last-minute regression | Golden path fails after polish | Tag stable build at Hour 18; smoke test each change | Revert to tagged demo build |

### Time-triggered cuts

- **At Hour 6:** if semantic extraction is not working, use cached CodeBERT embeddings for training/demo while completing the other three live signal groups.
- **At Hour 10:** if the MLP is unstable, freeze logistic regression.
- **At Hour 12:** if live GitHub ingestion is unreliable, prioritize ZIP plus cached public-repo demo.
- **At Hour 16:** if UI integration is incomplete, remove export and secondary charts.
- **At Hour 18:** all feature development stops.

---

## 15. Demo script (five minutes)

### 0:00–0:35 — Frame the problem

> “Generic AI-code detectors ask whether code looks like AI. That is unreliable and ignores the individual developer. CodeDNA asks a narrower question: does this submission behave like the student's own historical code?”

State the boundary:

> “It is a review-support system, not proof of misconduct.”

### 0:35–1:20 — Build the profile

- Show two historical repository inputs.
- Start profile creation.
- Point out filtering, deduplication, parsing, and embedding progress.
- Move to the completed cached profile if live processing would consume demo time.

Say:

> “The same pipeline extracts lexical habits, AST structure, complexity, and frozen CodeBERT representations. We never execute the student's code.”

### 1:20–1:55 — Show Code DNA

- Show analyzed file/function counts and profile confidence.
- Highlight two stable historical habits.
- Explain that the profile stores distributions, not just one average score.

### 1:55–2:40 — Authentic submission

- Analyze a held-out genuine file.
- Show a high consistency score and component agreement.
- Point out that it was not included in the enrollment profile.

### 2:40–3:35 — Anomalous/style-imitation submission

- Analyze the prepared anomalous submission.
- Show the lower score and **Review Recommended** verdict.
- Reveal high lexical similarity but lower AST/complexity/semantic similarity.
- Highlight the Surface–Structure Consistency Gap.

Say:

> “The naming style was made similar, but deeper program behaviour still shifted. CodeDNA makes that disagreement visible.”

### 3:35–4:15 — Explain the evidence

- Show top deviations with historical value, submission value, and z-score.
- Show analyzed/skipped-file coverage.
- Point to the human-review notice.

### 4:15–4:45 — Prove the ML work

- Show the three-row ablation table and held-out-author protocol.
- State the actual author/file/pair counts and actual F1/FPR.

Say:

> “We trained a fusion model over four independent signal families and evaluated it on authors excluded from training. The split is by author, not by file, to reduce leakage.”

### 4:45–5:00 — Close

> “CodeDNA turns an unreliable universal AI-detection claim into personalized, explainable behavioural authentication. It tells reviewers what changed and how strongly, while leaving the final judgment to a human.”

### Demo contingency

If network ingestion fails, say once:

> “The network path is unavailable, so I’m switching to the identical cached artifacts from our rehearsed repository.”

Then continue immediately. Do not debug on stage.

---

## 16. Judging talking points and likely questions

### “Are you claiming to detect AI-generated code?”

No. The model estimates consistency with a supplied historical developer profile. AI assistance is one possible reason for a deviation, along with collaboration, a new framework, learning, copied code, or a genuine style change. The system provides evidence for human review.

### “What is technically original?”

The project reframes global AI-code classification as personalized behavioural authentication. Its project-specific signal, the Surface–Structure Consistency Gap, measures when easy-to-copy surface habits agree poorly with deeper structural, complexity, and semantic behaviour.

### “What did you actually train?”

A fusion model over lexical, AST, complexity, semantic similarity, and the Surface–Structure Gap. CodeBERT is a frozen feature backbone. Show the saved model configuration and ablation results.

### “How did you avoid data leakage?”

Enrollment and query files are separate, duplicates are removed before splitting, and evaluation holds out claimed authors using grouped folds. No held-out query contributes to its profile.

### “Why not fine-tune CodeBERT?”

The dataset is too small for a credible fine-tune in 24 hours. Freezing the backbone and training a small fusion layer reduces overfitting and lets the evaluation focus on multimodal evidence.

### “How accurate is it?”

Answer only with the actual held-out metrics, sample sizes, and variance. Immediately state that the dataset is a prototype-scale benchmark and needs broader, longitudinal validation before institutional use.

### “What happens as students improve?”

The prototype can produce an uncertain result when evidence is mixed. A production system should update profiles gradually with verified submissions and model temporal drift. Automatic temporal adaptation is a post-MVP feature because unverified flagged code must not contaminate the baseline.

### “Can a student game lexical features?”

That is why CodeDNA combines surface, structural, complexity, and semantic signals. SSCG specifically surfaces cases where naming looks familiar but deeper behaviours disagree. It raises robustness; it does not make evasion impossible.

### “What about privacy and fairness?”

The system analyzes code supplied for a defined review purpose, minimizes retained data, and shows uncertainty and limitations. It must not be the sole basis for discipline. Production deployment would require consent/authority, retention controls, subgroup evaluation, appeals, and audit logs.

### “Why Python only?”

Python-only support allows one language to be parsed, normalized, tested, and explained well in the hackathon. The architecture has replaceable language adapters, but unsupported adapters are not presented as complete.

---

## 17. Post-MVP stretch gates

Stretch features are sequential. Start only when the preceding gate is satisfied and at least two hours remain before feature freeze.

### Gate A — Quality gate

Required:

- golden path passes twice;
- required evaluation and ablation are complete;
- five critical failure states pass;
- cached demo works;
- documentation skeleton exists.

**Allowed stretch:** per-function heat map using contribution/deviation aggregation. This strengthens explainability and the live demo without changing the model.

### Gate B — Scientific gate

Required:

- Gate A complete;
- at least six authors in grouped evaluation;
- thresholds frozen;
- no unresolved leakage concern.

**Allowed stretch:** three-case style-imitation stress test and SSCG comparison. Label it exploratory.

### Gate C — Product gate

Required:

- Gate B complete;
- UI is responsive and accessible;
- one timed rehearsal is under five minutes.

**Allowed stretch:** downloadable HTML/PDF-style report or JSON evidence export.

### Gate D — Extra-team-capacity gate

Required:

- dedicated owner who is not needed for bugs, docs, or rehearsal;
- no changes to the frozen feature schema.

**Allowed stretch:** lightweight commit-history summary such as commit count, burst size, and timestamp distribution. Keep it visually separate from the trained fusion score unless it has been evaluated.

### Explicitly deferred beyond the hackathon

- verified temporal profile updating;
- multi-language adapters;
- private-repository OAuth;
- institution-scale bias and subgroup evaluation;
- adversarial benchmark with multiple LLMs;
- calibrated open-set authorship verification on a large corpus;
- teacher feedback loop and case audit trail;
- LMS integration and production data governance.

---

## 18. Documentation and evidence checklist

The repository should contain:

- `README.md`: problem, product, setup, run commands, demo path;
- `ARCHITECTURE.md`: diagram, modules, data flow, API contract;
- `MODEL_CARD.md`: intended use, data, features, training, metrics, thresholds, limitations, ethical boundaries;
- `EVALUATION.md`: split protocol, pair construction, baselines, results, leakage controls;
- `DEMO.md`: five-minute script and fallback steps;
- `DATA_MANIFEST.csv`: source/permission and counts without unnecessary personal data;
- `results.json`: exact machine-readable metrics;
- `model/`: scaler, model, threshold config, schema/version metadata;
- `tests/`: meaningful extractor, validation, scoring, and API tests.

Before presenting, verify every slide number against `results.json`. Avoid aspirational architecture boxes for anything not implemented. Mark cached and live paths clearly in internal notes, while ensuring cached results were produced by the real pipeline.

---

## 19. Final build priority

If time pressure forces cuts, preserve work in this order:

1. complete profile-to-report golden path;
2. correct feature extraction and deterministic explanations;
3. real trained fusion model and author-grouped evaluation;
4. reliable cached demo and critical error states;
5. polished three-screen UI;
6. documentation and evidence pack;
7. optional stress test or report export;
8. every other feature.

The winning version is the one that can prove its claims in five minutes: a narrow product that works, a trained component with leakage-aware benchmarking, an original and visible consistency-gap idea, honest uncertainty, and a polished explanation of what changed.

## Implementation continuation log — 23 September 2026

- **Gate A completed:** the report now includes a ranked function-level heat map for lexical, structural, and complexity deviation.
- The heat map is explanatory only and does not alter the frozen fusion score or verdict thresholds.
- It is included in the live report, evidence JSON, and standalone HTML report.
- **Validation:** 45 automated tests pass, including API presence, bounded signal values, and descending deviation ranking.
- **Next gate:** Gate B remains closed because the current grouped evaluation has four repository-owner proxy labels; the plan requires at least six author labels and no unresolved leakage concern before style-imitation stress testing.
- **Calibration correction:** overlapping held-out score distributions now expand the Uncertain band instead of forcing a narrow band. The deployed false-positive rate fell from 0.521 at the fixed comparison threshold to 0.105 at the calibrated Consistent threshold, with 0.329 recall and 0.612 uncertainty reported as explicit tradeoffs.

