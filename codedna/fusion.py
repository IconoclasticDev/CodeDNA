"""Serializable NumPy logistic fusion model."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

MODEL_PATH = Path(__file__).resolve().parent / "artifacts" / "fusion_model.json"


@dataclass
class FusionModel:
    weights: list[float]
    bias: float
    means: list[float]
    scales: list[float]
    thresholds: dict[str, float]
    representation: str = "ast-token-hash-v1"
    name: str = "CodeDNA logistic fusion"

    def predict_probability(self, features: list[float]) -> float:
        values = np.asarray(features, dtype=float)
        normalized = (values - np.asarray(self.means)) / np.maximum(np.asarray(self.scales), 1e-8)
        logit = float(normalized @ np.asarray(self.weights) + self.bias)
        return float(1.0 / (1.0 + np.exp(-np.clip(logit, -35, 35))))

    def save(self, path: Path = MODEL_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"kind": "logistic", **self.__dict__}, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> "FusionModel":
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload.pop("kind", None)
        return cls(**payload)


@dataclass
class MLPFusionModel:
    weights_1: list[list[float]]
    bias_1: list[float]
    weights_2: list[list[float]]
    bias_2: list[float]
    weights_3: list[list[float]]
    bias_3: float
    means: list[float]
    scales: list[float]
    thresholds: dict[str, float]
    representation: str = "ast-token-hash-v1"
    name: str = "CodeDNA 5-16-8 fusion head"

    def predict_probability(self, features: list[float]) -> float:
        values = np.asarray(features, dtype=float)
        normalized = (values - np.asarray(self.means)) / np.maximum(np.asarray(self.scales), 1e-8)
        hidden_1 = np.maximum(0.0, normalized @ np.asarray(self.weights_1) + np.asarray(self.bias_1))
        hidden_2 = np.maximum(0.0, hidden_1 @ np.asarray(self.weights_2) + np.asarray(self.bias_2))
        logit = float(hidden_2 @ np.asarray(self.weights_3).reshape(-1) + self.bias_3)
        return float(1.0 / (1.0 + np.exp(-np.clip(logit, -35, 35))))

    def save(self, path: Path = MODEL_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"kind": "mlp", **self.__dict__}, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> "MLPFusionModel":
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload.pop("kind", None)
        return cls(**payload)


def train_logistic(
    features: np.ndarray,
    labels: np.ndarray,
    *,
    learning_rate: float = 0.08,
    epochs: int = 1800,
    l2: float = 0.015,
) -> FusionModel:
    features = np.asarray(features, dtype=float)
    labels = np.asarray(labels, dtype=float)
    means = features.mean(axis=0)
    scales = features.std(axis=0)
    normalized = (features - means) / np.maximum(scales, 1e-8)
    weights = np.zeros(normalized.shape[1], dtype=float)
    bias = 0.0
    for _ in range(epochs):
        logits = np.clip(normalized @ weights + bias, -35, 35)
        predictions = 1.0 / (1.0 + np.exp(-logits))
        error = predictions - labels
        weights -= learning_rate * ((normalized.T @ error) / len(labels) + l2 * weights)
        bias -= learning_rate * float(error.mean())
    return FusionModel(
        weights=weights.tolist(),
        bias=bias,
        means=means.tolist(),
        scales=np.maximum(scales, 1e-8).tolist(),
        thresholds={"consistent": 0.70, "review": 0.40},
    )


def train_mlp(
    features: np.ndarray,
    labels: np.ndarray,
    *,
    learning_rate: float = 0.025,
    epochs: int = 1400,
    l2: float = 0.008,
    dropout: float = 0.15,
    seed: int = 17,
) -> MLPFusionModel:
    features = np.asarray(features, dtype=float)
    labels = np.asarray(labels, dtype=float).reshape(-1, 1)
    means = features.mean(axis=0)
    scales = np.maximum(features.std(axis=0), 1e-8)
    x = (features - means) / scales
    rng = np.random.default_rng(seed)
    w1 = rng.normal(0, np.sqrt(2 / 5), size=(5, 16))
    b1 = np.zeros((1, 16))
    w2 = rng.normal(0, np.sqrt(2 / 16), size=(16, 8))
    b2 = np.zeros((1, 8))
    w3 = rng.normal(0, np.sqrt(2 / 8), size=(8, 1))
    b3 = np.zeros((1, 1))
    keep = 1.0 - dropout

    for _ in range(epochs):
        z1 = x @ w1 + b1
        a1 = np.maximum(0.0, z1)
        mask = (rng.random(a1.shape) < keep).astype(float)
        a1_drop = a1 * mask / keep
        z2 = a1_drop @ w2 + b2
        a2 = np.maximum(0.0, z2)
        logits = np.clip(a2 @ w3 + b3, -35, 35)
        predictions = 1.0 / (1.0 + np.exp(-logits))

        dz3 = (predictions - labels) / len(labels)
        dw3 = a2.T @ dz3 + l2 * w3
        db3 = dz3.sum(axis=0, keepdims=True)
        da2 = dz3 @ w3.T
        dz2 = da2 * (z2 > 0)
        dw2 = a1_drop.T @ dz2 + l2 * w2
        db2 = dz2.sum(axis=0, keepdims=True)
        da1 = (dz2 @ w2.T) * mask / keep
        dz1 = da1 * (z1 > 0)
        dw1 = x.T @ dz1 + l2 * w1
        db1 = dz1.sum(axis=0, keepdims=True)

        w3 -= learning_rate * dw3
        b3 -= learning_rate * db3
        w2 -= learning_rate * dw2
        b2 -= learning_rate * db2
        w1 -= learning_rate * dw1
        b1 -= learning_rate * db1

    return MLPFusionModel(
        weights_1=w1.tolist(), bias_1=b1.reshape(-1).tolist(),
        weights_2=w2.tolist(), bias_2=b2.reshape(-1).tolist(),
        weights_3=w3.tolist(), bias_3=float(b3.item()),
        means=means.tolist(), scales=scales.tolist(),
        thresholds={"consistent": 0.70, "review": 0.40},
    )


def load_model(path: Path = MODEL_PATH) -> FusionModel | MLPFusionModel:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("kind") == "mlp":
        return MLPFusionModel.load(path)
    return FusionModel.load(path)


def load_default_model() -> FusionModel | MLPFusionModel | None:
    return load_model() if MODEL_PATH.exists() else None
