"""summaries.py — monthly summary builders for Post- and PreKalkulacja."""
from __future__ import annotations

import pandas as pd
from modules.utils.matching import fcol


def build_post_summary(df: pd.DataFrame, grp_col: str) -> pd.DataFrame:
    """Build per-month, per-client summary for Postkalkulacja."""
    rows = []
    months = sorted(df["Miesiąc faktury"].dropna().unique())
    for month in months:
        df_m = df[df["Miesiąc faktury"] == month]
        if grp_col not in df_m.columns:
            continue
        for kl, grp in df_m.groupby(grp_col):
            sv = grp["Sales Value"].sum()
            tpm = grp["TPM"].sum()
            cm = grp["CM"].sum()
            rows.append({
                "Miesiąc": month,
                "Klient": kl,
                "Suma sprzedaży": sv,
                "Suma TPM": tpm,
                "TPM %": tpm / sv if sv else 0,
                "Suma CM": cm,
                "CM %": cm / sv if sv else 0,
                "Zamówień": len(grp),
                "Digital": (grp["Digital/Offset"] == "Digital").sum()
                if "Digital/Offset" in grp.columns else 0,
                "Offset": (grp["Digital/Offset"] == "Offset").sum()
                if "Digital/Offset" in grp.columns else 0,
                "No printing": (grp["Digital/Offset"] == "no printing").sum()
                if "Digital/Offset" in grp.columns else 0,
            })
    return pd.DataFrame(rows)


def build_prekalk_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Build per-month, per-client summary for PreKalkulacja."""
    if df is None or df.empty:
        return pd.DataFrame()
    klient_col = fcol(df, "Klient", "Klient z Orders", "Klient ID")
    if not klient_col:
        klient_col = "Zlecenie produkcyjne"
    rows = []
    for month, grp_m in df.groupby("Miesiąc faktury"):
        for klient, kgrp in grp_m.groupby(klient_col):
            sv = kgrp["Sales Value"].sum()
            tpm = kgrp["TPM"].sum()
            cm = kgrp["CM"].sum()
            rows.append({
                "Miesiąc faktury": month,
                "Nazwa klienta": klient,
                "Sales Value": sv,
                "TPM": tpm,
                "CM": cm,
                "TPM%": tpm / sv if sv != 0 else 0.0,
                "CM%": cm / sv if sv != 0 else 0.0,
            })
    return pd.DataFrame(rows)
