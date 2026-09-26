"""Generate presentation-ready benchmark evidence from real evaluation JSON."""

from __future__ import annotations

import csv
import html
import io
from pathlib import Path

SYSTEM_LABELS = {
    "semantic_only": "AST-token only",
    "engineered_only": "Engineered signals",
    "full_fusion": "CodeDNA fusion",
}
COLORS = {"semantic_only": "#a9a39a", "engineered_only": "#6952e8", "full_fusion": "#151512"}


def benchmark_svg(result: dict) -> str:
    summary = result["evaluation"]["summary"]
    systems = [name for name in ("semantic_only", "engineered_only", "full_fusion") if name in summary]
    metrics = [("roc_auc", "ROC-AUC"), ("f1", "F1"), ("false_positive_rate", "False positive rate")]
    width, height = 980, 530
    chart_left, chart_top, chart_width, chart_height = 105, 115, 800, 300
    group_width = chart_width / len(metrics)
    bar_width = 52
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f4f1e8"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#151512}.mono{font-family:monospace}.muted{fill:#6f7069}</style>',
        '<text x="48" y="52" font-size="26" font-weight="700">CodeDNA held-out-author benchmark</text>',
        '<text x="48" y="78" font-size="13" class="muted">Generated from evaluation results — values are never hard-coded</text>',
    ]
    for tick in range(6):
        value = tick / 5
        y = chart_top + chart_height - value * chart_height
        parts.append(f'<line x1="{chart_left}" y1="{y:.1f}" x2="{chart_left + chart_width}" y2="{y:.1f}" stroke="#d9d4c6"/>')
        parts.append(f'<text x="{chart_left - 15}" y="{y + 4:.1f}" text-anchor="end" font-size="11" class="mono muted">{value:.1f}</text>')
    for metric_index, (metric, label) in enumerate(metrics):
        center = chart_left + group_width * (metric_index + 0.5)
        total_bar_width = len(systems) * bar_width + (len(systems) - 1) * 12
        start = center - total_bar_width / 2
        for system_index, system in enumerate(systems):
            value = max(0.0, min(1.0, float(summary[system][metric])))
            x = start + system_index * (bar_width + 12)
            y = chart_top + chart_height - value * chart_height
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{value * chart_height:.1f}" fill="{COLORS[system]}"/>')
            parts.append(f'<text x="{x + bar_width / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-size="11" class="mono">{value:.2f}</text>')
        parts.append(f'<text x="{center:.1f}" y="{chart_top + chart_height + 28}" text-anchor="middle" font-size="13" font-weight="700">{html.escape(label)}</text>')
    legend_y = 482
    legend_width = 220
    legend_start = (width - legend_width * len(systems)) / 2
    for index, system in enumerate(systems):
        x = legend_start + index * legend_width
        parts.append(f'<rect x="{x:.1f}" y="{legend_y - 12}" width="14" height="14" fill="{COLORS[system]}"/>')
        parts.append(f'<text x="{x + 23:.1f}" y="{legend_y}" font-size="12">{html.escape(SYSTEM_LABELS[system])}</text>')
    parts.append("</svg>")
    return "".join(parts)


def evidence_markdown(result: dict) -> str:
    dataset = result["dataset"]
    evaluation = result["evaluation"]
    thresholds = evaluation["calibrated_thresholds"]
    lines = [
        "# CodeDNA evaluation evidence",
        "",
        "This file is generated from the machine-readable evaluation result.",
        "",
        f"- Authors: **{dataset['authors']}**",
        f"- Files: **{dataset['files']}**",
        f"- Balanced profile/query pairs: **{dataset['pairs']}**",
        f"- Protocol: **{evaluation['protocol']}**",
        f"- Selected fusion: **{evaluation.get('selected_fusion', 'full_fusion')}**",
        "",
        "| System | ROC-AUC | F1 | F1 std | Precision | Recall | False-positive rate | Brier |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ("semantic_only", "engineered_only", "full_fusion"):
        metrics = evaluation["summary"][name]
        lines.append(
            f"| {SYSTEM_LABELS[name]} | {metrics['roc_auc']:.3f} | {metrics['f1']:.3f} | "
            f"{metrics['f1_std']:.3f} | {metrics['precision']:.3f} | {metrics['recall']:.3f} | "
            f"{metrics['false_positive_rate']:.3f} | {metrics['brier_score']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Calibrated three-way verdict",
            "",
            f"- Review Recommended below **{thresholds['review']:.3f}**",
            f"- Uncertain from **{thresholds['review']:.3f}** to **{thresholds['consistent']:.3f}**",
            f"- Consistent at or above **{thresholds['consistent']:.3f}**",
            f"- Observed false-review rate: **{thresholds['observed_false_review_rate']:.3f}**",
            f"- Observed impostor-consistent rate: **{thresholds['observed_impostor_consistent_rate']:.3f}**",
            f"- Overall uncertain rate: **{evaluation.get('calibrated_operating_point', {}).get('uncertain_rate', 0.0):.3f}**",
            "",
            "The comparison table uses the conventional fixed 0.50 threshold. The rates above describe the deployed three-way operating point, where ambiguous cases abstain into **Uncertain**.",
            "",
            f"> {result['limitation']}",
            "",
        ]
    )
    return "\n".join(lines)


def confusion_matrix_svg(result: dict) -> str:
    """Render out-of-fold binary counts without recomputing predictions."""
    evaluation = result["evaluation"]
    counts = evaluation.get("calibrated_operating_point", evaluation["full_fusion_out_of_fold"])
    threshold = float(counts.get("threshold", 0.5))
    cells = [
        ("TN", "Impostor → inconsistent", int(counts["tn"]), "#d9ff58"),
        ("FP", "Impostor → consistent", int(counts["fp"]), "#ffb09f"),
        ("FN", "Genuine → inconsistent", int(counts["fn"]), "#ffcf7b"),
        ("TP", "Genuine → consistent", int(counts["tp"]), "#6952e8"),
    ]
    width, height = 820, 560
    x_positions = (260, 500)
    y_positions = (155, 345)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f4f1e8"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#151512}.mono{font-family:monospace}.muted{fill:#6f7069}</style>',
        '<text x="42" y="48" font-size="26" font-weight="700">CodeDNA out-of-fold confusion matrix</text>',
        f'<text x="42" y="75" font-size="13" class="muted">Selected fusion · calibrated consistent threshold {threshold:.3f}</text>',
        '<text x="380" y="112" text-anchor="middle" font-size="13" font-weight="700">Predicted class</text>',
        '<text x="380" y="532" text-anchor="middle" font-size="12" class="muted">Counts are generated from held-out-author predictions in results.json</text>',
        '<text x="360" y="137" text-anchor="middle" font-size="12">Inconsistent</text>',
        '<text x="600" y="137" text-anchor="middle" font-size="12">Consistent</text>',
        '<text x="75" y="250" text-anchor="middle" font-size="13" font-weight="700" transform="rotate(-90 75 250)">Actual class</text>',
        '<text x="225" y="245" text-anchor="end" font-size="12">Impostor</text>',
        '<text x="225" y="435" text-anchor="end" font-size="12">Genuine</text>',
    ]
    for index, (short, label, value, color) in enumerate(cells):
        column = index % 2
        row = index // 2
        x, y = x_positions[column], y_positions[row]
        text_color = "#ffffff" if short == "TP" else "#151512"
        parts.extend(
            [
                f'<rect x="{x}" y="{y}" width="200" height="160" fill="{color}" stroke="#151512"/>',
                f'<text x="{x + 18}" y="{y + 27}" font-size="12" class="mono" fill="{text_color}">{short}</text>',
                f'<text x="{x + 100}" y="{y + 91}" text-anchor="middle" font-size="46" font-weight="700" fill="{text_color}">{value}</text>',
                f'<text x="{x + 100}" y="{y + 126}" text-anchor="middle" font-size="11" fill="{text_color}">{html.escape(label)}</text>',
            ]
        )
    parts.append("</svg>")
    return "".join(parts)


def fold_csv(result: dict) -> str:
    """Return the selected model's per-fold metrics as portable CSV."""
    evaluation = result["evaluation"]
    selected = evaluation["selected_fusion"]
    fields = [
        "fold", "held_out_authors", "test_pairs", "model", "roc_auc", "f1",
        "precision", "recall", "false_positive_rate", "brier_score", "tp", "fp", "fn", "tn",
    ]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for index, fold in enumerate(evaluation["folds"], start=1):
        metrics = fold[selected]
        writer.writerow(
            {
                "fold": index,
                "held_out_authors": ";".join(fold["held_out_authors"]),
                "test_pairs": fold["test_pairs"],
                "model": selected,
                **{field: metrics[field] for field in fields[4:]},
            }
        )
    return stream.getvalue()


def write_benchmark_artifacts(result: dict, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    chart = output_dir / "benchmark.svg"
    confusion = output_dir / "confusion_matrix.svg"
    folds = output_dir / "fold_metrics.csv"
    evidence = output_dir / "EVIDENCE.md"
    chart.write_text(benchmark_svg(result), encoding="utf-8")
    confusion.write_text(confusion_matrix_svg(result), encoding="utf-8")
    folds.write_text(fold_csv(result), encoding="utf-8", newline="")
    evidence.write_text(evidence_markdown(result), encoding="utf-8")
    return {
        "benchmark_chart": str(chart),
        "confusion_matrix": str(confusion),
        "fold_metrics": str(folds),
        "evidence_markdown": str(evidence),
    }
