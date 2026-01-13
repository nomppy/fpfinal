from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd


def char_ngrams(text: str, n_min: int, n_max: int) -> Iterable[str]:
    clean = "".join(ch for ch in text if not ch.isspace())
    for n in range(n_min, n_max + 1):
        for i in range(0, len(clean) - n + 1):
            yield clean[i : i + n]


def log_odds(counter_a: Counter, counter_b: Counter, alpha: float) -> Dict[str, float]:
    vocab = set(counter_a.keys()) | set(counter_b.keys())
    a_total = sum(counter_a.values())
    b_total = sum(counter_b.values())
    scores = {}
    for term in vocab:
        a = counter_a.get(term, 0) + alpha
        b = counter_b.get(term, 0) + alpha
        score = np.log(a / (a_total + alpha)) - np.log(b / (b_total + alpha))
        scores[term] = float(score)
    return scores


def chi_square(counter_a: Counter, counter_b: Counter) -> Dict[str, float]:
    vocab = set(counter_a.keys()) | set(counter_b.keys())
    a_total = sum(counter_a.values())
    b_total = sum(counter_b.values())
    scores = {}
    for term in vocab:
        a = counter_a.get(term, 0)
        b = counter_b.get(term, 0)
        expected_a = (a_total * (a + b)) / (a_total + b_total)
        expected_b = (b_total * (a + b)) / (a_total + b_total)
        score = 0.0
        if expected_a > 0:
            score += (a - expected_a) ** 2 / expected_a
        if expected_b > 0:
            score += (b - expected_b) ** 2 / expected_b
        scores[term] = float(score)
    return scores


def compute_keyness(
    high_texts: List[str],
    low_texts: List[str],
    n_min: int,
    n_max: int,
    method: str,
    alpha: float,
    top_n: int,
) -> pd.DataFrame:
    high = Counter()
    low = Counter()
    for text in high_texts:
        high.update(char_ngrams(text, n_min, n_max))
    for text in low_texts:
        low.update(char_ngrams(text, n_min, n_max))
    if method == "chi_square":
        scores = chi_square(high, low)
    else:
        scores = log_odds(high, low, alpha)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return pd.DataFrame([{"ngram": term, "score": score} for term, score in ranked])

