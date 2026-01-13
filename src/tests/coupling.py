from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.tests.trend import quarterly_bin


def pearson_corr(x: List[float], y: List[float]) -> float:
    if len(x) < 2:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def cohens_d(x: List[float], y: List[float]) -> float:
    if len(x) < 2 or len(y) < 2:
        return 0.0
    nx, ny = len(x), len(y)
    sx, sy = np.var(x, ddof=1), np.var(y, ddof=1)
    pooled = ((nx - 1) * sx + (ny - 1) * sy) / (nx + ny - 2)
    if pooled == 0:
        return 0.0
    return float((np.mean(x) - np.mean(y)) / np.sqrt(pooled))


def _is_mfa_source(source_type: str) -> bool:
    return source_type in {"mfa_presser", "mfa_pressers"}


def run_coupling(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    records = []
    for row in rows:
        if not _is_mfa_source(row["source_type"]):
            continue
        bin_id = quarterly_bin(row["date"])
        records.append(
            {
                "bin": bin_id,
                "outward": row["scores"]["outward_axis"],
                "security": row["scores"]["security_axis"],
                "growth": row["scores"]["growth_axis"],
                "is_outward": row["scores"].get("is_outward", False),
            }
        )
    if not records:
        return pd.DataFrame(columns=["bin", "corr_outward_security", "corr_outward_growth", "d_security", "d_growth"])
    df = pd.DataFrame(records)
    out = []
    for bin_id, group in df.groupby("bin"):
        out.append(
            {
                "bin": bin_id,
                "corr_outward_security": pearson_corr(group["outward"].tolist(), group["security"].tolist()),
                "corr_outward_growth": pearson_corr(group["outward"].tolist(), group["growth"].tolist()),
                "d_security": cohens_d(
                    group.loc[group["is_outward"], "security"].tolist(),
                    group.loc[~group["is_outward"], "security"].tolist(),
                ),
                "d_growth": cohens_d(
                    group.loc[group["is_outward"], "growth"].tolist(),
                    group.loc[~group["is_outward"], "growth"].tolist(),
                ),
            }
        )
    return pd.DataFrame(out).sort_values("bin")
