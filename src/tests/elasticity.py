from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from src.tests.slogans import entropy_from_counts


def cluster_embeddings(embeddings: np.ndarray, k: int, random_state: int) -> np.ndarray:
    model = KMeans(n_clusters=k, random_state=random_state, n_init=10)
    return model.fit_predict(embeddings)


def slogan_entropy(
    slogan_to_segments: Dict[str, List[int]],
    cluster_labels: np.ndarray,
    bins: Dict[int, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows = []
    series_rows = []
    for slogan, indices in slogan_to_segments.items():
        label_counts = np.bincount(cluster_labels[indices])
        entropy = entropy_from_counts(label_counts.tolist())
        summary_rows.append({"slogan": slogan, "entropy": entropy})
        by_bin = {}
        for idx in indices:
            bin_id = bins.get(idx)
            if bin_id is None:
                continue
            by_bin.setdefault(bin_id, []).append(cluster_labels[idx])
        for bin_id, labels in by_bin.items():
            counts = np.bincount(labels)
            series_rows.append({"slogan": slogan, "bin": bin_id, "entropy": entropy_from_counts(counts.tolist())})
    return pd.DataFrame(summary_rows), pd.DataFrame(series_rows)

