"""profitability_engine.py — core PostKalkulacja calculation engine."""
from __future__ import annotations

import re
import numpy as np
import pandas as pd
import streamlit as st

from modules.readers.baza_reader import read_post_list
from modules.readers.generic_reader import read_generic, read_with_header_detect
from modules.utils.matching import fcol, norm_df
from modules.utils.helpers import sn, batch_label, rate_for_machine, extract_fry_fragment


# ── Classification helpers ────────────────────────────────────────────────────

def classify_do(zp: str, czasy_idx: dict[str, set]) -> str:
    zp = str(zp).strip()
    if zp not in czasy_idx:
        return ""
    machines = czasy_idx[zp]
    HP_KW = {"hp35k", "hp7k", "hp 35", "hp 7", "hp 1", "hp indigo"}
    HD_KW = {"heidelberg cx 104", "heidelberg cx104", "heidelberg"}
    is_hp = any(any(kw in m for kw in HP_KW) for m in machines)
    is_hd = any(any(kw in m for kw in HD_KW) for m in machines)
    if is_hp:
        return "Digital"
    if is_hd:
        return "Offset"
    return "no printing"


def exclude_oticon_zam_rows(df: pd.DataFrame, klient_col: str | None = None) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    zam_c = fcol(df, "Zamówienie", "Zamowienie")
    if not zam_c:
        return df
    if not klient_col or klient_col not in df.columns:
        klient_col = fcol(df, "Klient", "Klient ID")
    if not klient_col or klient_col not in df.columns:
        return df
    client_mask = df[klient_col].fillna("").astype(str).str.contains(
        r"Oticon\s*A/S\s*/\s*DGS\s*Denmark|Oticon|DGS\s*Denmark",
        case=False, regex=True, na=False,
    )
    zam_mask = df[zam_c].fillna("").astype(str).str.contains(
        "ZAM", case=False, regex=False, na=False,
    )
    return df.loc[~(client_mask & zam_mask)].copy()


# ── Farby reader ──────────────────────────────────────────────────────────────

def read_farby_pivot(uf) -> pd.DataFrame | None:
    if uf is None:
        return None
    try:
        import io
        raw = uf.read()
        uf.seek(0)
        xl = pd.ExcelFile(io.BytesIO(raw))
        sheet = next(
            (s for s in xl.sheet_names if "pivot" in s.lower() or "farb" in s.lower()),
            xl.sheet_names[0],
        )
        probe = pd.read_excel(io.BytesIO(raw), sheet_name=sheet, header=None, nrows=8)
        hrow = 0
        for i, row in probe.iterrows():
            vals = [str(v).strip() for v in row.dropna()]
            if "Etykiety wierszy" in vals or "Suma koszt farby2" in vals:
                hrow = i
                break
        df = pd.read_excel(io.BytesIO(raw), sheet_name=sheet, header=hrow)
        return norm_df(df)
    except Exception as exc:
        st.warning(f"⚠️ Błąd pliku Farby: {exc}")
        return None


def read_click_costs(uf) -> dict[str, dict[str, float]]:
    if uf is None:
        return {}
    try:
        import io
        raw = uf.read()
        uf.seek(0)
        probe = pd.read_excel(io.BytesIO(raw), header=None, nrows=15)
        hrow = 0
        for i, row in probe.iterrows():
            vals = [str(v).strip().lower() for v in row.dropna()]
            if (any(v in {"maszyna", "press name", "machine", "maszyna (press name)"} for v in vals)
                    and any("koszt" in v or "cost" in v for v in vals)):
                hrow = i
                break
        df = pd.read_excel(io.BytesIO(raw), header=hrow)
        df = norm_df(df)
        mach_c = fcol(df, "Maszyna (Press Name)", "Press Name", "Maszyna", "Machine")
        color_c = fcol(df, "Kolor", "Color")
        cost_c = fcol(df, "Koszt PLN/sep", "Koszt", "Cost", "Click cost",
                      "Koszt klików", "Koszt klikow")
        if not (mach_c and cost_c):
            return {}
        if not color_c:
            df["Kolor"] = "default"
            color_c = "Kolor"
        out: dict[str, dict[str, float]] = {}
        for _, row in df.dropna(subset=[mach_c]).iterrows():
            mach = str(row.get(mach_c, "")).strip()
            color = str(row.get(color_c, "default")).strip() or "default"
            if mach:
                out.setdefault(mach, {})[color] = sn(row.get(cost_c, 0))
        return out
    except Exception as exc:
        st.warning(f"⚠️ Błąd kosztów klików: {exc}")
        return {}


# ── Main engine ───────────────────────────────────────────────────────────────

def build_profitability(
    uf_base,
    uf_czasy,
    uf_zlec,
    uf_fry,
    uf_inks,
    uf_farby,
    rates: dict,
    click_costs: dict,
    prepress: dict,
    pp_digital: float,
    pp_offset: float,
    other_pct: float,
) -> tuple[dict | None, list[str]]:
    """
    Main PostKalkulacja calculation.
    Returns (result_dict, warnings_list).
    """
    warns: list[str] = []

    # ── 1. BASE ───────────────────────────────────────────────────────────────
    df = read_post_list(uf_base)
    if df is None:
        return None, ["Nie można wczytać pliku Bazy."]

    numer_c = fcol(df, "Numer")
    zam_c = fcol(df, "Zamówienie")
    qty_c = fcol(df, "Zamawiana ilość", "Zamawiana ilosc")
    klient_c = fcol(df, "Klient", "Klient ID")

    for req_col in ["Numer", "Zamówienie", "Zamawiana ilość"]:
        if fcol(df, req_col) is None:
            warns.append(f"Brak wymaganej kolumny w Bazie: '{req_col}'")

    df["Zlecenie produkcyjne"] = (
        df[numer_c].astype(str).str.split("-").str[0].str.strip()
        if numer_c else ""
    )
    df["Lewy 10"] = df[zam_c].astype(str).str[:10] if zam_c else ""
    df["Batch"] = df[qty_c].apply(batch_label) if qty_c else ""

    # ── 2. CZASY ─────────────────────────────────────────────────────────────
    df_czasy_raw = read_generic(uf_czasy)
    machine_cols: list[str] = []
    czasy_idx: dict[str, set] = {}

    if df_czasy_raw is not None:
        nzp_c = fcol(df_czasy_raw, "Numer zlecenia produkcyjnego")
        nm_c = fcol(df_czasy_raw, "Nazwa maszyny")
        czas_c = fcol(df_czasy_raw, "Czas czynnosci [min]", "Czas czynności [min]")

        if nzp_c and nm_c and czas_c:
            df_czasy_raw[nzp_c] = df_czasy_raw[nzp_c].astype(str).str.strip()
            df_czasy_raw[nm_c] = df_czasy_raw[nm_c].astype(str).str.strip()
            df_czasy_raw[czas_c] = pd.to_numeric(
                df_czasy_raw[czas_c], errors="coerce"
            ).fillna(0)

            for zp, grp in df_czasy_raw.groupby(nzp_c):
                czasy_idx[zp] = set(grp[nm_c].str.lower())

            df_czasy_raw["_rate"] = df_czasy_raw[nm_c].apply(
                lambda m: rate_for_machine(m, rates)
            )
            df_czasy_raw["Koszt pracy"] = (
                df_czasy_raw[czas_c] / 60.0 * df_czasy_raw["_rate"]
            )

            machines = sorted(df_czasy_raw[nm_c].dropna().unique())
            machine_cols = [str(m).strip() for m in machines]

            pivot = (
                df_czasy_raw.pivot_table(
                    index=nzp_c, columns=nm_c,
                    values="Koszt pracy", aggfunc="sum", fill_value=0,
                ).reset_index()
            )
            pivot.columns = [str(c).strip() for c in pivot.columns]
            pivot.rename(columns={nzp_c: "_zp_key"}, inplace=True)

            df = df.merge(
                pivot,
                left_on="Zlecenie produkcyjne",
                right_on="_zp_key",
                how="left",
            )
            df.drop(columns=["_zp_key"], errors="ignore", inplace=True)
            for mc in machine_cols:
                if mc in df.columns:
                    df[mc] = pd.to_numeric(df[mc], errors="coerce").fillna(0)
                else:
                    df[mc] = 0.0
        else:
            warns.append("Plik Czasy: brak kolumn NZP / Nazwa maszyny / Czas.")
            df_czasy_raw = None
    elif uf_czasy:
        warns.append("Nie można wczytać pliku Czasy.")

    df["Digital/Offset"] = df["Zlecenie produkcyjne"].apply(
        lambda zp: classify_do(zp, czasy_idx)
    )

    if not machine_cols:
        warns.append("Brak pliku Czasy – Total DL z Prepress costs only.")

    # ── 3. FARBY ─────────────────────────────────────────────────────────────
    df_farby_pivot = read_farby_pivot(uf_farby)

    if df_farby_pivot is not None:
        ew_c = fcol(df_farby_pivot, "Etykiety wierszy")
        kf_c = fcol(df_farby_pivot, "Suma koszt farby2")
        kp_c = fcol(df_farby_pivot, "Suma koszt płyty", "Suma koszt plyty")
        if ew_c and kf_c and kp_c:
            df_farby_pivot[ew_c] = df_farby_pivot[ew_c].astype(str).str.strip()
            df_fp = (
                df_farby_pivot[[ew_c, kf_c, kp_c]]
                .rename(columns={ew_c: "_ew", kf_c: "Offset inks", kp_c: "Płyta offsetowa"})
            )
            df_fp["_ew"] = df_fp["_ew"].str[:10]
            df_fp = df_fp.groupby("_ew").sum().reset_index()
            df = df.merge(df_fp, left_on="Lewy 10", right_on="_ew", how="left")
            df.drop(columns=["_ew"], errors="ignore", inplace=True)
        else:
            warns.append("Plik Farby: brak kolumn Etykiety / koszt farby / koszt płyty.")
    else:
        if uf_farby:
            warns.append("Nie można wczytać pliku Farby.")

    df["Offset inks"] = pd.to_numeric(df.get("Offset inks"), errors="coerce").fillna(0)
    df["Płyta offsetowa"] = pd.to_numeric(df.get("Płyta offsetowa"), errors="coerce").fillna(0)

    # ── 4. KLIKI / INKS ──────────────────────────────────────────────────────
    df_kliki_out = None

    if uf_inks:
        try:
            import io as _io
            raw_inks = uf_inks.read()
            uf_inks.seek(0)
            df_inks = norm_df(pd.read_excel(_io.BytesIO(raw_inks)))
            jn_c = fcol(df_inks, "Job Name")
            pn_c = fcol(df_inks, "Press Name")
            col_c = fcol(df_inks, "Color")
            sep_c = fcol(df_inks, "Separations")

            if jn_c and sep_c:
                df_inks["Zamówienie"] = df_inks[jn_c].astype(str).str[:10]
                df_inks["_seps"] = pd.to_numeric(
                    df_inks[sep_c], errors="coerce"
                ).fillna(0)

                def _unit_cost(row) -> float:
                    mach = str(row.get(pn_c, "")).strip() if pn_c else ""
                    color = str(row.get(col_c, "")).strip() if col_c else ""
                    cc = click_costs.get(mach, {})
                    return cc.get(
                        color,
                        cc.get(
                            "default",
                            next((v.get("default", .05) for v in click_costs.values()), .05),
                        ),
                    )

                df_inks["Koszt klików"] = df_inks.apply(_unit_cost, axis=1) * df_inks["_seps"]
                grp_inks = (
                    df_inks.groupby("Zamówienie")["Koszt klików"]
                    .sum()
                    .reset_index()
                    .rename(columns={"Zamówienie": "_zk", "Koszt klików": "Moje Kliki"})
                )
                df = df.merge(grp_inks, left_on="Lewy 10", right_on="_zk", how="left")
                df.drop(columns=["_zk"], errors="ignore", inplace=True)
                df_kliki_out = df_inks.drop(columns=["_seps"], errors="ignore")
            else:
                warns.append("Plik Inks: brak kolumn Job Name / Separations.")
        except Exception as exc:
            warns.append(f"Błąd pliku Inks: {exc}")

    df["Moje Kliki"] = pd.to_numeric(df.get("Moje Kliki"), errors="coerce").fillna(0)
    kliki48_c = fcol(df, "Kliki [48]")
    if kliki48_c:
        df[kliki48_c] = pd.to_numeric(df[kliki48_c], errors="coerce").fillna(0)
        df["Kliki final"] = df[[kliki48_c, "Moje Kliki"]].max(axis=1)
    else:
        df["Kliki final"] = df["Moje Kliki"]

    # ── 5. SALES VALUE & DATA FAKTURY ────────────────────────────────────────
    df["Sales Value"] = np.nan
    df["Data faktury"] = pd.NaT

    if uf_zlec:
        df_zlec = read_generic(uf_zlec)
        if df_zlec is not None:
            nzp_z = fcol(df_zlec, "Numer zlecenia produkcyjnego")
            wart_z = fcol(df_zlec, "Wartosc w linii FV netto", "Wartość w linii FV netto")
            data_z = fcol(df_zlec, "Data wystawienia FV", "Data wystawienia faktury")

            if nzp_z and wart_z:
                df_zlec["_nzp"] = df_zlec[nzp_z].astype(str).str.strip()
                agg_dict: dict = {wart_z: "sum"}
                if data_z:
                    agg_dict[data_z] = "first"
                grp_z = df_zlec.groupby("_nzp").agg(agg_dict).reset_index()
                grp_z = grp_z.rename(columns={
                    "_nzp": "_znzp",
                    wart_z: "_sv_z",
                    **({data_z: "_dv_z"} if data_z else {}),
                })
                df = df.merge(grp_z, left_on="Zlecenie produkcyjne",
                              right_on="_znzp", how="left")
                mask_z = df["_sv_z"].notna()
                df.loc[mask_z, "Sales Value"] = df.loc[mask_z, "_sv_z"]
                if "_dv_z" in df.columns:
                    df.loc[mask_z, "Data faktury"] = pd.to_datetime(
                        df.loc[mask_z, "_dv_z"], errors="coerce"
                    )
                df.drop(
                    columns=[c for c in df.columns if c.startswith("_")],
                    errors="ignore", inplace=True,
                )

    missing_mask = df["Sales Value"].isna()
    if uf_fry and missing_mask.any():
        import io as _io2
        df_fry = read_generic(uf_fry)
        if df_fry is not None:
            nl_c = fcol(df_fry, "Nazwa linii faktury")
            wl_c = fcol(df_fry, "Wartosc w linii FV netto", "Wartość w linii FV netto")
            il_c = fcol(df_fry, "Ilosc w linii FV")
            dl_c = fcol(df_fry, "Data wystawienia FV")

            if nl_c and wl_c:
                fry_nl_lower = [s.lower() for s in df_fry[nl_c].fillna("").astype(str).tolist()]

                for idx in df[missing_mask].index:
                    zam_val = str(df.at[idx, zam_c] if zam_c else "").strip()
                    qty_val = sn(df.at[idx, qty_c] if qty_c else 0)
                    frag = extract_fry_fragment(zam_val)
                    found_row = None
                    if frag:
                        frag_lower = frag.lower()
                        matched = [i for i, s in enumerate(fry_nl_lower) if frag_lower in s]
                        if matched:
                            found_row = df_fry.iloc[matched[0]]
                    if found_row is None:
                        continue
                    wart_fry = sn(found_row[wl_c])
                    ilosc_fry = sn(found_row[il_c]) if il_c else 0
                    sv = (
                        (wart_fry / ilosc_fry) * qty_val
                        if ilosc_fry > 0 and qty_val > 0
                        else wart_fry
                    )
                    df.at[idx, "Sales Value"] = sv
                    if dl_c:
                        df.at[idx, "Data faktury"] = pd.to_datetime(
                            found_row[dl_c], errors="coerce"
                        )

    df["Sales Value"] = pd.to_numeric(df["Sales Value"], errors="coerce").fillna(0)
    df["Data faktury"] = pd.to_datetime(df["Data faktury"], errors="coerce")
    df["Miesiąc faktury"] = df["Data faktury"].dt.strftime("%Y-%m")

    # ── 6. PREPRESS ───────────────────────────────────────────────────────────
    def _prepress(row) -> float:
        klient = str(row.get(klient_c, "") if klient_c else "").strip()
        oi = sn(row.get("Offset inks", 0))
        cfg = prepress.get(klient, {})
        if cfg:
            return cfg.get(
                "offset" if oi > 0 else "digital",
                pp_offset if oi > 0 else pp_digital,
            )
        return pp_offset if oi > 0 else pp_digital

    df["Prepress costs"] = df.apply(_prepress, axis=1)

    # ── 7. OTHER MATERIALS ────────────────────────────────────────────────────
    df["Other Materials"] = df["Sales Value"] * (other_pct / 100.0)

    # ── 8. TOTAL DL ──────────────────────────────────────────────────────────
    dl_components = machine_cols + ["Prepress costs"]
    for col in dl_components:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["Total DL"] = df[dl_components].sum(axis=1)

    # ── 9. TOTAL MATERIALS ────────────────────────────────────────────────────
    MAT_NAMES = [
        "Papier [16]", "Klej [17]", "Lakiery [20]",
        "Opakowania zbiorcze [24]", "Other Materials",
        "Offset inks", "Płyta offsetowa", "Kliki final",
    ]
    mat_cols_used: list[str] = []
    for mc in MAT_NAMES:
        rc = fcol(df, mc)
        if rc:
            df[rc] = pd.to_numeric(df[rc], errors="coerce").fillna(0)
            mat_cols_used.append(rc)
        else:
            df[mc] = 0.0
            mat_cols_used.append(mc)
    df["Total Materials"] = df[mat_cols_used].sum(axis=1)

    # ── 10. TPM & CM ─────────────────────────────────────────────────────────
    df["TPM"] = df["Sales Value"] - df["Total DL"]
    df["CM"] = df["Sales Value"] - df["Total DL"] - df["Total Materials"]

    # ── 11. COLUMN ORDER ─────────────────────────────────────────────────────
    TAIL = ["Total DL", "Total Materials", "Sales Value",
            "Data faktury", "Miesiąc faktury", "TPM", "CM"]
    other_cols = [c for c in df.columns if c not in TAIL]
    df = df[[c for c in other_cols + TAIL if c in df.columns]]
    df = df[[c for c in df.columns if not c.startswith("_")]]

    return {
        "df_prof": df,
        "df_czasy": df_czasy_raw,
        "df_kliki": df_kliki_out,
        "df_farby_pivot": df_farby_pivot,
        "machine_cols": machine_cols,
        "mat_cols": mat_cols_used,
        "klient_col": klient_c,
        "qty_col": qty_c,
        "warns": warns,
    }, warns
