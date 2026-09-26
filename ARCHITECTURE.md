# CodeDNA architecture

## Runtime flow

```text
Local .py files / safe ZIP / public GitHub repository
                         │
                         ▼
             validation and bounded ingestion
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
    invalid/excluded log       eligible Python files
                                      │
                                      ▼
                 lexical + AST + complexity + AST-token vector
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
              historical profile          submission features
                         └────────────┬────────────┘
                                      ▼
             four similarities + Surface–Structure Gap
                                      │
                     trained fusion model when available
                     deterministic baseline otherwise
                                      │
                                      ▼
              score + verdict + deviations + limitations
```

## Modules

| Module | Responsibility |
|---|---|
| `codedna/ingest.py` | Strict public-GitHub URL validation and bounded safe ZIP extraction |
| `codedna/collect.py` | Permission-aware, commit-pinned multi-author dataset collection |
| `codedna/features.py` | Lexical, AST and complexity feature extraction |
| `codedna/semantic.py` | Offline AST-token vector fallback; explicitly not CodeBERT |
| `codedna/codebert.py` | Optional frozen CodeBERT inference, boundary-aware chunking and cache |
| `codedna/representation.py` | Provider selection, readiness and compatibility contract |
| `codedna/profile.py` | Deduplication, aggregate statistics, stability and centroid construction |
| `codedna/scoring.py` | Similarity inputs, SSCG, verdict and deterministic explanations |
| `codedna/fusion.py` | Serializable NumPy logistic and custom 5→16→8→1 neural fusion models |
| `codedna/train.py` | Dataset loading, pair creation, author-grouped evaluation and final training |
| `codedna/storage.py` | Atomic local profile persistence |
| `codedna/server.py` | JSON API and static frontend server |

## Trust boundaries

- Repository code is decoded and parsed but never imported or executed.
- Public repository collection accepts only exact `https://github.com/{owner}/{repository}` URLs, then downloads through fixed GitHub API and codeload hosts.
- Training collection resolves a requested branch/tag to a 40-character commit SHA before downloading, preserving the immutable SHA in the resolved manifest.
- ZIP extraction is performed in memory. Absolute paths, `..` traversal, symlinks, excluded directories, oversized archives and oversized members are rejected or skipped.
- API bodies are capped at 5 MB. Archives are capped at 25 MB compressed and 50 MB uncompressed.
- Profiles are stored locally under `work/runtime/profiles` and are not transmitted elsewhere.

## API contract

### `POST /api/profiles`

At least one source is required:

```json
{
  "name": "Developer",
  "files": [{"name": "one.py", "content": "..."}],
  "archive_base64": "optional-base64-zip",
  "repository_urls": ["https://github.com/owner/repository"]
}
```

### `POST /api/profiles/{id}/analyze`

Accepts `files` or `archive_base64`. Repository URL analysis is supported by the backend but should be used only when the submission source is itself a repository.

## Model compatibility contract

The fusion model always receives values in this order:

```text
[lexical_similarity, structural_similarity, complexity_similarity,
 ast_token_similarity, surface_structure_gap]
```

The model artifact stores weights, bias, scaling means, scaling standard deviations, verdict thresholds and representation identity in one JSON file. Frozen CodeBERT can replace the fourth feature behind the same normalized `[0,1]` contract. Profiles and trained models record the provider name, and incompatible combinations are rejected. Provider changes require profile rebuilding and fusion retraining.
