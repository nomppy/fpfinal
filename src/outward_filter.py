from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

import numpy as np


def compute_year_thresholds(rows: List[Dict[str, Any]], percentile: float) -> Dict[Tuple[str, str], float]:
    by_group: Dict[Tuple[str, str], List[float]] = defaultdict(list)
    for row in rows:
        year = row["date"][:4]
        by_group[(year, row["source_type"])] .append(row["scores"]["outward_axis"])
    thresholds = {}
    for key, values in by_group.items():
        thresholds[key] = float(np.percentile(values, percentile * 100)) if values else 0.0
    return thresholds


def mark_outward(rows: List[Dict[str, Any]], thresholds: Dict[Tuple[str, str], float]) -> None:
    for row in rows:
        key = (row["date"][:4], row["source_type"])
        row["scores"]["is_outward"] = row["scores"]["outward_axis"] >= thresholds.get(key, 0.0)

