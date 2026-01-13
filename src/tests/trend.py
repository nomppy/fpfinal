from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


def quarterly_bin(date_str: str) -> str:
    month = int(date_str[5:7])
    quarter = (month - 1) // 3 + 1
    return f"{date_str[:4]}-Q{quarter}"


def length_weighted_mean(values: List[float], weights: List[int]) -> float:
    if not values:
        return 0.0
    w = np.array(weights, dtype=float)
    v = np.array(values, dtype=float)
    return float((v * w).sum() / w.sum()) if w.sum() > 0 else 0.0


def _is_mfa_source(source_type: str) -> bool:
    return source_type in {"mfa_presser", "mfa_pressers"}


def run_trend(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    records = []
    for row in rows:
        if not row["scores"].get("is_outward"):
            continue
        bin_id = quarterly_bin(row["date"]) if _is_mfa_source(row["source_type"]) else row["date"]
        records.append(
            {
                "bin": bin_id,
                "source_type": row["source_type"],
                "security": row["scores"]["security_axis"],
                "growth": row["scores"]["growth_axis"],
                "char_len": row["char_len"],
            }
        )
    if not records:
        return pd.DataFrame(columns=["bin", "source_type", "security_mean", "growth_mean", "n_segments"])
    df = pd.DataFrame(records)
    out = []
    for (bin_id, source_type), group in df.groupby(["bin", "source_type"]):
        out.append(
            {
                "bin": bin_id,
                "source_type": source_type,
                "security_mean": length_weighted_mean(group["security"].tolist(), group["char_len"].tolist()),
                "growth_mean": length_weighted_mean(group["growth"].tolist(), group["char_len"].tolist()),
                "n_segments": int(group.shape[0]),
            }
        )
    return pd.DataFrame(out).sort_values(["bin", "source_type"])
