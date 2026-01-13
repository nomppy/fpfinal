from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from src.embed import EmbeddingEngine


def build_axis_vectors(axes_cfg: Dict[str, Any], embedder: EmbeddingEngine) -> Dict[str, np.ndarray]:
    axes = {}
    for key, axis in axes_cfg.items():
        seeds: List[str] = axis["seeds"]
        emb = embedder.embed_texts(seeds)
        axis_vec = emb.mean(axis=0)
        axis_vec = axis_vec / np.linalg.norm(axis_vec)
        axes[key] = axis_vec
    return axes


def score_segments(embeddings: np.ndarray, axes: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    scores = {}
    for name, axis_vec in axes.items():
        scores[name] = embeddings @ axis_vec
    return scores

