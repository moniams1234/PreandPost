"""helpers.py — pure utility functions with no Streamlit dependency."""
from __future__ import annotations

import re
import numpy as np
from typing import Any


def sn(val: Any) -> float:
    """Safe numeric conversion; returns 0.0 on failure."""
    try:
        v = float(val)
        return 0.0 if (np.isnan(v) or np.isinf(v)) else v
    except (TypeError, ValueError):
        return 0.0


def batch_label(qty: Any) -> str:
    """Return batch-range string for a quantity value."""
    try:
        q = float(str(qty).strip().replace(",", "."))
    except (TypeError, ValueError):
        return ""
    if q <= 50:
        return "0-50"
    if q <= 100:
        return "51-100"
    if q <= 200:
        return "101-200"
    if q <= 300:
        return "201-300"
    if q <= 500:
        return "301-500"
    if q <= 1000:
        return "501-1000"
    if q <= 1500:
        return "1001-1500"
    if q <= 2000:
        return "1501-2000"
    if q <= 3000:
        return "2001-3000"
    if q <= 10000:
        return "3001-10000"
    if q <= 20000:
        return "10001-20000"
    if q <= 30000:
        return "20001-30000"
    if q <= 100000:
        return "30001-100000"
    return "100001-1000000"


def rate_for_machine(machine: Any, rates: dict) -> float:
    """Fuzzy-match machine name to rate dict.

    Robust against empty/NaN/non-string machine names and malformed rate values.
    This prevents Streamlit Cloud crashes when a source file has blank machine rows.
    """
    if machine is None:
        return 0.0

    try:
        # pandas/pyarrow can pass NA-like or numeric values here
        if isinstance(machine, float) and (np.isnan(machine) or np.isinf(machine)):
            return 0.0
    except Exception:
        pass

    ml = str(machine).strip().lower()
    if not ml or ml in {"nan", "none", "<na>", "nat"}:
        return 0.0

    safe_rates = rates or {}

    for k, v in safe_rates.items():
        kl = str(k).strip().lower()
        if kl and kl == ml:
            return sn(v)

    for k, v in safe_rates.items():
        kl = str(k).strip().lower()
        if kl and (kl in ml or ml in kl):
            return sn(v)

    m_words = {w for w in re.split(r"\W+", ml) if len(w) >= 2}
    best, best_v = 0, 0.0
    for k, v in safe_rates.items():
        kl = str(k).strip().lower()
        kw = {w for w in re.split(r"\W+", kl) if len(w) >= 2}
        score = len(m_words & kw)
        if score > best:
            best, best_v = score, sn(v)

    return best_v


def extract_fry_fragment(zamowienie: str) -> str:
    """Extract fragment used to match against Nazwa linii faktury."""
    s = str(zamowienie).strip()
    if "| " in s:
        frag = s.split("| ", 1)[1].strip()
        frag = re.sub(r"\s*\[.*$", "", frag).strip()
        if frag:
            return frag
    tokens = re.findall(r"[A-Za-z0-9\-]{5,}", s)
    return tokens[0] if tokens else ""
