"""profitability_engine.py — core PostKalkulacja calculation engine."""
from __future__ import annotations

import re
import numpy as np
import pandas as pd
import streamlit as st

from modules.readers.baza_reader import read_post_list
from modules.readers.generic_reader import read_generic, read_with_header_detect
from modules.readers.czasy_reader import read_czasy
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
    df_czasy_raw = read_czasy(uf_czasy)
    machine_cols: list[str] = []
    czasy_idx: dict[str, set] = {}

    if df_czasy_raw is not None:
        nzp_c = fcol(df_czasy_raw, "Numer zlecenia produkcyjnego")
        nm_c = fcol(df_czasy_raw, "Nazwa maszyny")
        czas_c = fcol(df_czasy_raw, "Czas czynnosci [min]", "Czas czynności [min]", "Suma z Czas czynnosci [min]", "Suma z Czas czynności [min]", "Czas [min]", "Czas")

        if nzp_c and nm_c and czas_c:
            df_czasy_raw[nzp_c] = df_czasy_raw[nzp_c].astype(str).str.strip()
            df_czasy_raw[nm_c] = df_czasy_raw[nm_c].fillna("").astype(str).str.strip()
            df_czasy_raw = df_czasy_raw[df_czasy_raw[nm_c] != ""].copy()
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
    # Sales Value priority:
    # 1) If "Wartość faktur" / "Wartosc faktur" in base Profitability has value != 0,
    #    use it directly.
    # 2) If it is zero/empty, use zlecenia + faktury by Numer zlecenia produkcyjnego:
    #    - one positive row -> take it
    #    - many positive rows -> match by Ilosc w linii FV
    #    - negative corrections for the same production order are added only once
    #      using a "used correction" mechanism per production order.
    # 3) If still missing and client is not FD Pharma, use Faktury-linie fallback
    #    only for non-empty, non-TEST, produced rows.
    # 4) If no allowed match exists -> Sales Value = 0.
    df_zlec = None
    df["Sales Value"] = np.nan
    df["Data faktury"] = pd.NaT
    df["_matched_source"] = ""

    qty_fv_base_col = fcol(df, "Zamawiana ilość z FV", "Zamawiana ilosc z FV")
    if not qty_fv_base_col:
        qty_fv_base_col = fcol(df, "Zamawiana ilość", "Zamawiana ilosc")

    invoice_value_col = fcol(df, "Wartość faktur", "Wartosc faktur", "Wartość faktury", "Wartosc faktury")
    used_negative_corrections: set[str] = set()

    # ── 5a. Base Profitability: Wartość faktur ───────────────────────────────
    if invoice_value_col:
        base_invoice_values = pd.to_numeric(df[invoice_value_col], errors="coerce").fillna(0)
        mask_base_invoice = base_invoice_values != 0
        df.loc[mask_base_invoice, "Sales Value"] = base_invoice_values.loc[mask_base_invoice]
        df.loc[mask_base_invoice, "_matched_source"] = "Wartość faktur"

    # ── 5b. zlecenia + faktury ───────────────────────────────────────────────
    if uf_zlec:
        df_zlec = read_generic(uf_zlec)
        if df_zlec is not None:
            nzp_z = fcol(df_zlec, "Numer zlecenia produkcyjnego")
            wart_z = fcol(df_zlec, "Wartosc w linii FV netto", "Wartość w linii FV netto")
            data_z = fcol(df_zlec, "Data wystawienia FV", "Data wystawienia faktury")
            ilosc_z = fcol(df_zlec, "Ilosc w linii FV", "Ilość w linii FV")

            if nzp_z and wart_z:
                zlec = df_zlec.copy()
                zlec["_nzp"] = zlec[nzp_z].astype(str).str.strip()
                zlec["_sales"] = pd.to_numeric(zlec[wart_z], errors="coerce")
                zlec["_date"] = pd.to_datetime(zlec[data_z], errors="coerce") if data_z else pd.NaT
                zlec["_qty"] = pd.to_numeric(zlec[ilosc_z], errors="coerce") if ilosc_z else np.nan
                groups_z = {k: g.copy() for k, g in zlec.groupby("_nzp", dropna=False)}

                def _sales_plus_negative(pos_row, group_all, zp_key: str):
                    base_sales = float(pos_row["_sales"]) if pd.notna(pos_row["_sales"]) else 0.0
                    negative_sum = 0.0
                    # Negative correction can be used only once per production order.
                    if zp_key not in used_negative_corrections:
                        negative_sum = group_all.loc[
                            group_all["_sales"].fillna(0) < 0,
                            "_sales"
                        ].sum(skipna=True)
                        used_negative_corrections.add(zp_key)
                    return base_sales + float(negative_sum)

                def _match_sales_from_zlec(row):
                    # If Sales Value already came from Wartość faktur, do not search further.
                    existing_sv = pd.to_numeric(row.get("Sales Value", np.nan), errors="coerce")
                    if pd.notna(existing_sv):
                        return pd.Series([existing_sv, row.get("Data faktury", pd.NaT), row.get("_matched_source", "")])

                    zp = str(row.get("Zlecenie produkcyjne", "")).strip()
                    if not zp or zp not in groups_z:
                        return pd.Series([np.nan, pd.NaT, "brak w zlec+FV"])

                    g = groups_z[zp].copy()
                    g_valid = g[g["_sales"].notna()].copy()
                    if g_valid.empty:
                        return pd.Series([np.nan, pd.NaT, "zlec+FV: brak wartości"])

                    positives = g_valid[g_valid["_sales"] >= 0].copy()
                    if positives.empty:
                        return pd.Series([np.nan, pd.NaT, "zlec+FV: tylko korekty ujemne"])

                    if len(positives) == 1:
                        r = positives.iloc[0]
                        return pd.Series([
                            _sales_plus_negative(r, g_valid, zp),
                            r["_date"],
                            "zlec+FV: NZP + korekty ujemne"
                        ])

                    if qty_fv_base_col:
                        q = pd.to_numeric(row.get(qty_fv_base_col, np.nan), errors="coerce")
                        try:
                            q = float(q)
                        except Exception:
                            q = np.nan

                        if pd.notna(q):
                            gm = positives[
                                np.isclose(
                                    positives["_qty"].fillna(-999999).astype(float),
                                    q,
                                    atol=0.01,
                                )
                            ]
                            if len(gm) >= 1:
                                r = gm.iloc[0]
                                return pd.Series([
                                    _sales_plus_negative(r, g_valid, zp),
                                    r["_date"],
                                    "zlec+FV: NZP + ilość FV + korekty ujemne"
                                ])

                    return pd.Series([np.nan, pd.NaT, "zlec+FV: brak dopasowania ilości"])

                # Apply only to rows still missing Sales Value.
                rows_for_zlec = df["Sales Value"].isna()
                if rows_for_zlec.any():
                    matched_sales = df.loc[rows_for_zlec].apply(_match_sales_from_zlec, axis=1)
                    matched_sales.columns = ["_matched_sales", "_matched_date", "_matched_source"]

                    # Data faktury priority: zlec+FV first.
                    # Assign zlec+FV date whenever the production order is matched,
                    # even if Sales Value was already taken from "Wartość faktur".
                    mask_date_zlec = matched_sales["_matched_date"].notna()
                    idx_date = matched_sales.loc[mask_date_zlec].index
                    df.loc[idx_date, "Data faktury"] = matched_sales.loc[idx_date, "_matched_date"].values

                    # Sales Value from zlec+FV only for rows still empty after "Wartość faktur".
                    rows_for_zlec_sales = df.loc[matched_sales.index, "Sales Value"].isna()
                    mask_sales = matched_sales["_matched_sales"].notna() & rows_for_zlec_sales
                    idx_sales = matched_sales.loc[mask_sales].index
                    df.loc[idx_sales, "Sales Value"] = matched_sales.loc[idx_sales, "_matched_sales"].values
                    df.loc[idx_sales, "_matched_source"] = matched_sales.loc[idx_sales, "_matched_source"].values

                    # Keep diagnostics where source is still blank.
                    blank_source = df.loc[matched_sales.index, "_matched_source"].fillna("").astype(str).str.strip() == ""
                    common_idx = matched_sales.loc[blank_source].index
                    df.loc[common_idx, "_matched_source"] = matched_sales.loc[common_idx, "_matched_source"].values

    # ── 5c. Faktury-linie fallback: blocked for FD Pharma and invalid rows ────
    missing_mask = df["Sales Value"].isna()

    klient_col_for_fallback = klient_c if klient_c and klient_c in df.columns else fcol(df, "Klient")
    zam_col_for_fallback = zam_c if zam_c and zam_c in df.columns else fcol(df, "Zamówienie", "Zamowienie")

    fallback_machine_cols = [c for c in machine_cols if c in df.columns] if "machine_cols" in locals() else []

    def _allow_invoice_line_fallback(row) -> bool:
        klient_val = str(row.get(klient_col_for_fallback, "") if klient_col_for_fallback else "").strip().lower()
        zam_val = str(row.get(zam_col_for_fallback, "") if zam_col_for_fallback else "").strip()

        if klient_val == "fd pharma":
            return False
        if not zam_val:
            return False
        if "test" in zam_val.lower():
            return False
        if fallback_machine_cols:
            vals = pd.to_numeric(row.reindex(fallback_machine_cols), errors="coerce").fillna(0)
            if not (vals > 0).any():
                return False
        return True

    if uf_fry and missing_mask.any():
        df_fry = read_generic(uf_fry)
        if df_fry is not None:
            nl_c = fcol(df_fry, "Nazwa linii faktury")
            wl_c = fcol(df_fry, "Wartosc w linii FV netto", "Wartość w linii FV netto")
            il_c = fcol(df_fry, "Ilosc w linii FV", "Ilość w linii FV")
            dl_c = fcol(df_fry, "Data wystawienia FV")

            if nl_c and wl_c:
                fry_names = df_fry[nl_c].fillna("").astype(str).str.lower().tolist()

                for idx in df[missing_mask].index:
                    row = df.loc[idx]
                    if not _allow_invoice_line_fallback(row):
                        df.at[idx, "_matched_source"] = "fallback zablokowany"
                        df.at[idx, "Data faktury"] = pd.NaT
                        continue

                    zam_val = str(row.get(zam_col_for_fallback, "") if zam_col_for_fallback else "").strip()
                    lewy_val = str(row.get("Lewy 10", "") if "Lewy 10" in df.columns else "").strip()
                    qty_val = sn(row.get(qty_fv_base_col, 0)) if qty_fv_base_col else sn(row.get(qty_c, 0) if qty_c else 0)

                    candidates = []
                    frag = extract_fry_fragment(zam_val)
                    if frag:
                        candidates.append(frag)
                    if lewy_val:
                        candidates.append(lewy_val)

                    matched = []
                    for candidate in candidates:
                        c = str(candidate).strip().lower()
                        if c:
                            matched = [i for i, s in enumerate(fry_names) if c in s]
                            if matched:
                                break

                    if not matched:
                        continue

                    found_row = df_fry.iloc[matched[0]]
                    wart_fry = sn(found_row[wl_c])
                    ilosc_fry = sn(found_row[il_c]) if il_c else 0

                    if ilosc_fry > 0 and qty_val > 0:
                        sv = (wart_fry / ilosc_fry) * qty_val
                        source = "faktury linie: proporcja"
                    else:
                        sv = wart_fry
                        source = "faktury linie: wartość linii"

                    df.at[idx, "Sales Value"] = sv
                    df.at[idx, "_matched_source"] = source
                    if dl_c:
                        df.at[idx, "Data faktury"] = pd.to_datetime(found_row[dl_c], errors="coerce")

    df["Sales Value"] = pd.to_numeric(df["Sales Value"], errors="coerce").fillna(0)

    # Final date rule:
    # zlec+FV date has priority, then faktury linie date.
    # If fallback is blocked or Sales Value remains 0, date/month stay blank.
    blocked_or_zero = (
        df.get("_matched_source", "").astype(str).str.lower().eq("fallback zablokowany")
        | (df["Sales Value"] == 0)
    )
    df.loc[blocked_or_zero, "Data faktury"] = pd.NaT

    df["Data faktury"] = pd.to_datetime(df["Data faktury"], errors="coerce")
    df["Miesiąc faktury"] = df["Data faktury"].dt.strftime("%Y-%m")
    df["Źródło Sales Value"] = df.get("_matched_source", "")

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

    # ── 9b. CHECK SPRZEDAŻ ────────────────────────────────────────────────────
    qty_fv_col = fcol(df, "Zamawiana ilość z FV", "Zamawiana ilosc z FV")
    if not qty_fv_col:
        qty_fv_col = fcol(df, "Zamawiana ilość", "Zamawiana ilosc")
    sales_col = fcol(df, "Sales Value")

    if qty_fv_col and sales_col:
        qty_cmp = pd.to_numeric(df[qty_fv_col], errors="coerce").fillna(0)
        sales_cmp = pd.to_numeric(df[sales_col], errors="coerce").fillna(0)
        df["check sprzedaż"] = np.where(
            np.isclose(qty_cmp, sales_cmp, atol=0.01),
            "OK",
            "NOK",
        )
    else:
        df["check sprzedaż"] = ""

    # ── 10. TPM, CM, TPM% & CM% ──────────────────────────────────────────────
    # User definition:
    #   TPM  = Sales Value - Total Materials
    #   TPM% = 100% * TPM / Sales Value
    #   CM%  = 100% * CM  / Sales Value
    # CM remains contribution after direct labour:
    #   CM = Sales Value - Total Materials - Total DL
    df["TPM"] = df["Sales Value"] - df["Total Materials"]
    df["CM"] = df["Sales Value"] - df["Total Materials"] - df["Total DL"]
    df["TPM%"] = np.where(df["Sales Value"] != 0, df["TPM"] / df["Sales Value"], 0.0)
    df["CM%"] = np.where(df["Sales Value"] != 0, df["CM"] / df["Sales Value"], 0.0)

    # ── 11. COLUMN ORDER ─────────────────────────────────────────────────────
    TAIL = ["Total DL", "Total Materials", "Sales Value",
            "Data faktury", "Miesiąc faktury", "TPM", "TPM%", "CM", "CM%"]
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
