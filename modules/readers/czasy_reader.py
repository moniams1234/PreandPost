"""czasy_reader.py — robust reader for Czasy dla aplikacji."""
from __future__ import annotations

import io
import pandas as pd
import streamlit as st

from modules.readers.generic_reader import read_with_header_detect
from modules.utils.matching import norm_df, fcol


CZASY_REQUIRED_ALIASES = {
    "Numer zlecenia produkcyjnego": [
        "Numer zlecenia produkcyjnego", "NZP", "Zlecenie produkcyjne",
        "Numer zlecenia", "Nr zlecenia produkcyjnego",
    ],
    "Nazwa maszyny": [
        "Nazwa maszyny", "Maszyna", "Name", "Machine", "Machine name",
    ],
    "Czas czynnosci [min]": [
        "Czas czynnosci [min]", "Czas czynności [min]", "Suma z Czas czynnosci [min]",
        "Suma z Czas czynności [min]", "Czas [min]", "Czas",
    ],
}


def _detect_header_row(raw: bytes, sheet_name: str) -> int:
    """Find header row containing production order, machine and time columns."""
    probe = pd.read_excel(io.BytesIO(raw), sheet_name=sheet_name, header=None, nrows=30)
    best_row = 0
    best_score = -1

    header_keywords = [
        "numer zlecenia produkcyjnego", "nazwa maszyny", "czas czynnosci",
        "czas czynności", "suma z czas", "zakonczenie czynnosci",
        "zakończenie czynności", "naklad", "nakład",
    ]

    for i, row in probe.iterrows():
        vals = [" ".join(str(v).strip().lower().split()) for v in row.dropna()]
        if not vals:
            continue
        joined = " | ".join(vals)
        score = sum(1 for kw in header_keywords if kw in joined)
        # real header should have multiple descriptive columns, not data rows
        if score > best_score:
            best_score = score
            best_row = i

    return best_row


def _choose_sheet(raw: bytes) -> str | int:
    """Prefer PIVOT if present, otherwise BI/Raport sheet, otherwise first sheet."""
    xl = pd.ExcelFile(io.BytesIO(raw))
    names = xl.sheet_names

    for pattern in ("pivot", "bi - raport", "bi", "raport"):
        for s in names:
            if pattern in s.lower():
                return s
    return names[0] if names else 0


def _normalise_czasy_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename required czasy columns to canonical names."""
    df = norm_df(df)

    ren = {}
    nzp = fcol(df, *CZASY_REQUIRED_ALIASES["Numer zlecenia produkcyjnego"])
    mach = fcol(df, *CZASY_REQUIRED_ALIASES["Nazwa maszyny"])
    czas = fcol(df, *CZASY_REQUIRED_ALIASES["Czas czynnosci [min]"])

    if nzp:
        ren[nzp] = "Numer zlecenia produkcyjnego"
    if mach:
        ren[mach] = "Nazwa maszyny"
    if czas:
        ren[czas] = "Czas czynnosci [min]"

    df = df.rename(columns=ren)

    if "Czas czynnosci [min]" in df.columns:
        df["Czas czynnosci [min]"] = pd.to_numeric(
            df["Czas czynnosci [min]"], errors="coerce"
        ).fillna(0)

    if "Numer zlecenia produkcyjnego" in df.columns:
        df["Numer zlecenia produkcyjnego"] = (
            df["Numer zlecenia produkcyjnego"].astype(str).str.strip()
        )

    if "Nazwa maszyny" in df.columns:
        df["Nazwa maszyny"] = df["Nazwa maszyny"].astype(str).str.strip()

    return df


def read_czasy(uf) -> pd.DataFrame | None:
    """
    Robust reader for real 'czasy dla aplikacji' files.

    Supports:
    - sheet 'BI - Raport'
    - sheet 'PIVOT'
    - first sheet fallback
    - direct header in row 0
    - pivot/multi-row header with dynamic detection

    Returns dataframe with canonical columns:
    - Numer zlecenia produkcyjnego
    - Nazwa maszyny
    - Czas czynnosci [min]
    """
    if uf is None:
        return None

    try:
        raw = uf.read()
        uf.seek(0)

        sheet = _choose_sheet(raw)
        hrow = _detect_header_row(raw, sheet)
        df = pd.read_excel(io.BytesIO(raw), sheet_name=sheet, header=hrow)
        df = _normalise_czasy_columns(df)

        nzp = fcol(df, "Numer zlecenia produkcyjnego")
        mach = fcol(df, "Nazwa maszyny")
        czas = fcol(df, "Czas czynnosci [min]")

        if not (nzp and mach and czas):
            # fallback to generic reader if needed
            df2 = read_with_header_detect(raw, sheet=sheet)
            if df2 is not None:
                df2 = _normalise_czasy_columns(df2)
                nzp = fcol(df2, "Numer zlecenia produkcyjnego")
                mach = fcol(df2, "Nazwa maszyny")
                czas = fcol(df2, "Czas czynnosci [min]")
                if nzp and mach and czas:
                    return df2

            st.warning(
                "⚠️ Plik Czasy został wczytany, ale nie rozpoznano kolumn: "
                "Numer zlecenia produkcyjnego / Nazwa maszyny / Czas czynnosci [min]."
            )
            return df

        return df

    except Exception as exc:
        st.warning(f"⚠️ Błąd wczytywania Czasy: {exc}")
        return None


def read_czasy_pivot(uf) -> pd.DataFrame | None:
    """Backward-compatible alias for PreKalkulacja machine sheet."""
    return read_czasy(uf)


def read_stawki(uf) -> dict[str, float]:
    """Parse Stawki file → {machine_name: hourly_rate}."""
    if uf is None:
        return {}
    try:
        from modules.utils.matching import fcol
        from modules.utils.helpers import sn
        raw = uf.read()
        uf.seek(0)
        probe = pd.read_excel(io.BytesIO(raw), header=None, nrows=15)
        hrow = 0
        for i, row in probe.iterrows():
            vals = [str(v).strip().lower() for v in row.dropna()]
            if (any("nazwa maszyny" in v or "maszyna" == v for v in vals)
                    and any("stawka" in v for v in vals)):
                hrow = i
                break
        df = pd.read_excel(io.BytesIO(raw), header=hrow)
        df = norm_df(df)
        nm = fcol(df, "Nazwa maszyny", "Maszyna", "Machine", "Machine name")
        sr = fcol(df, "Stawka rbg", "Stawka rbg (PLN/h)", "RBG", "Rate", "Hourly rate", "PLN/h")
        if not (nm and sr):
            return {}
        return {
            str(r[nm]).strip(): sn(r[sr])
            for _, r in df.dropna(subset=[nm]).iterrows()
            if str(r[nm]).strip()
        }
    except Exception as exc:
        st.warning(f"⚠️ Błąd stawek rbg: {exc}")
        return {}
