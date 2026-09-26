# Optional frozen CodeBERT provider

The core CodeDNA application remains dependency-free apart from NumPy and uses the local `ast-token-hash-v1` representation. A frozen CodeBERT provider is implemented as an optional upgrade.

## Install the optional runtime

```powershell
python -m pip install -r requirements-codebert.txt
```

## Configure before starting the service

To use a model already available locally:

```powershell
$env:CODEDNA_REPRESENTATION = "codebert"
$env:CODEDNA_CODEBERT_MODEL = "C:\path\to\local\codebert"
.\start.ps1
```

To allow Hugging Face to download `microsoft/codebert-base` on first use:

```powershell
$env:CODEDNA_REPRESENTATION = "codebert"
$env:CODEDNA_ALLOW_MODEL_DOWNLOAD = "1"
.\start.ps1
```

Model downloads are disabled by default. This avoids an unexpected network operation during a demo.

## Implementation details

- Code is split primarily at top-level function and class boundaries.
- Each chunk is truncated to the model's 512-token limit.
- Token embeddings are attention-mask mean pooled.
- Chunk vectors are mean pooled and L2 normalized into one file vector.
- Vectors are cached by SHA-256 of the model identifier and source content.
- The model runs in evaluation mode with gradients disabled.
- CUDA is used when PyTorch reports it as available; otherwise inference uses the CPU.

Profiles record their representation provider. CodeDNA refuses to compare a CodeBERT submission with an AST-token profile, or to apply a fusion model trained with a different representation. Switching providers therefore requires rebuilding profiles and retraining the fusion model.

