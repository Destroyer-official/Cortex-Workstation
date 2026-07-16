"""Smart Suggestions - a tiny, fully-offline, on-device learning engine.

What it honestly is: an **online logistic-regression / contextual-bandit**
recommender. It learns which cleanup items you tend to approve vs. skip and
nudges future recommendations accordingly. It is deliberately *not* deep
reinforcement learning - that would cost real RAM/CPU/storage and contradict the
lightweight goal.

Properties:
* **Fully offline.** No network, ever. Pure stdlib (``math``, ``json``).
* **Tiny.** The model is a dict of ``feature -> weight`` floats, capped in size,
  persisted as a few-KB JSON under ``~/.cortex_cleaner``.
* **Cheap.** Prediction and update are O(number of active features) - a few
  dozen multiply-adds per item. No matrices, no training loops.
* **Transparent & safe.** It only *reorders/annotates* suggestions; it never
  deletes anything on its own and never overrides the safety guard.

Model: sigmoid(w . x) estimates P(user keeps/cleans this item). Weights are
updated by one SGD step of logistic loss whenever the user accepts (label 1) or
skips (label 0) a suggestion.
"""

from __future__ import annotations

import json
import logging
import math
import threading
from pathlib import Path
from typing import Any

_LOG = logging.getLogger("cortex.core.smart_suggest")

_MODEL_VERSION = 1
_MAX_FEATURES = 4000        # hard cap => bounded memory (~tens of KB)
_DEFAULT_LR = 0.15          # SGD learning rate
_L2 = 1e-4                  # tiny L2 regularization to keep weights bounded


def _sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def _size_bucket(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "sz:0"
    mb = size_bytes / (1024 * 1024)
    if mb < 1:
        return "sz:<1mb"
    if mb < 10:
        return "sz:1-10mb"
    if mb < 100:
        return "sz:10-100mb"
    if mb < 1024:
        return "sz:100mb-1gb"
    return "sz:>1gb"


def _age_bucket(age_days: float) -> str:
    if age_days < 1:
        return "age:<1d"
    if age_days < 7:
        return "age:1-7d"
    if age_days < 30:
        return "age:7-30d"
    if age_days < 180:
        return "age:30-180d"
    return "age:>180d"


def featurize(context: dict[str, Any]) -> list[str]:
    """Turn a cleanup item's context into a small list of active feature keys.

    Expected (all optional) context keys: ``category``, ``extension``,
    ``size`` (bytes), ``age_days`` (float), ``path`` (str).
    """
    feats: list[str] = ["bias"]
    cat = context.get("category")
    if cat:
        feats.append(f"cat:{str(cat).lower()}")
    ext = context.get("extension")
    if ext:
        feats.append(f"ext:{str(ext).lower().lstrip('.')[:12]}")
    if "size" in context and context["size"] is not None:
        feats.append(_size_bucket(int(context["size"])))
    if "age_days" in context and context["age_days"] is not None:
        feats.append(_age_bucket(float(context["age_days"])))
    path = context.get("path")
    if path:
        low = str(path).lower()
        for marker in ("temp", "cache", "log", "download", "appdata", "prefetch", "recycle"):
            if marker in low:
                feats.append(f"loc:{marker}")
    return feats


class SmartSuggester:
    """Online logistic-regression recommender with local JSON persistence."""

    def __init__(self, model_path: Path | None = None, learning_rate: float = _DEFAULT_LR):
        self._lock = threading.Lock()
        self._weights: dict[str, float] = {}
        self._lr = learning_rate
        self._updates = 0
        self._model_path = model_path or (Path.home() / ".cortex_cleaner" / "smart_model.json")
        self._load()

    # -- inference ----------------------------------------------------------

    def score(self, context: dict[str, Any]) -> float:
        """Return P(user would clean this item), in [0, 1]."""
        feats = featurize(context)
        with self._lock:
            z = sum(self._weights.get(f, 0.0) for f in feats)
        return _sigmoid(z)

    def recommend(self, context: dict[str, Any], threshold: float = 0.5) -> bool:
        """Whether to recommend cleaning this item (until trained, defaults to True)."""
        if self._updates < 10:      # not enough signal yet -> don't second-guess
            return True
        return self.score(context) >= threshold

    def rank(self, items: list[dict[str, Any]]) -> list[tuple[dict[str, Any], float]]:
        """Return items paired with scores, highest-confidence-to-clean first."""
        scored = [(it, self.score(it)) for it in items]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored

    # -- learning -----------------------------------------------------------

    def observe(self, context: dict[str, Any], cleaned: bool) -> None:
        """Update the model from one user decision (cleaned=True kept/removed it)."""
        feats = featurize(context)
        label = 1.0 if cleaned else 0.0
        with self._lock:
            z = sum(self._weights.get(f, 0.0) for f in feats)
            pred = _sigmoid(z)
            err = pred - label                      # gradient of logistic loss
            for f in feats:
                w = self._weights.get(f, 0.0)
                w -= self._lr * (err + _L2 * w)
                self._weights[f] = w
            self._updates += 1
            self._enforce_cap_locked()

    def observe_batch(self, items: list[dict[str, Any]], cleaned: bool) -> None:
        for it in items:
            self.observe(it, cleaned)

    def _enforce_cap_locked(self) -> None:
        """Keep the model tiny: if over cap, drop the smallest-magnitude weights."""
        if len(self._weights) <= _MAX_FEATURES:
            return
        keep = sorted(self._weights.items(), key=lambda kv: abs(kv[1]), reverse=True)[:_MAX_FEATURES]
        self._weights = dict(keep)

    # -- persistence --------------------------------------------------------

    def _load(self) -> None:
        try:
            if self._model_path.exists():
                data = json.loads(self._model_path.read_text(encoding="utf-8"))
                if data.get("version") == _MODEL_VERSION:
                    self._weights = {str(k): float(v) for k, v in data.get("weights", {}).items()}
                    self._updates = int(data.get("updates", 0))
        except Exception as exc:  # noqa: BLE001 - a corrupt model must never crash the app
            _LOG.debug("could not load smart model: %s", exc)
            self._weights = {}
            self._updates = 0

    def save(self) -> bool:
        """Persist the model atomically. Returns True on success."""
        try:
            self._model_path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                payload = {
                    "version": _MODEL_VERSION,
                    "updates": self._updates,
                    "weights": self._weights,
                }
            tmp = self._model_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            tmp.replace(self._model_path)
            return True
        except Exception as exc:  # noqa: BLE001
            _LOG.debug("could not save smart model: %s", exc)
            return False

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "updates": self._updates,
                "feature_count": len(self._weights),
                "trained": self._updates >= 10,
                "model_path": str(self._model_path),
            }

    def reset(self) -> None:
        with self._lock:
            self._weights.clear()
            self._updates = 0
