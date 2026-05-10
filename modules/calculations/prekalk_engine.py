"""prekalk_engine.py — full PreKalkulacja calculation engine."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from modules.utils.matching import fcol
from modules.utils.helpers import sn, rate_for_machine
from modules.readers.wydajnosc_reader import wydajnosc_as_dict


def build_prekalkulacja(
    result: dict | None,
    df_orders: pd.DataFrame | None,
    df_tektura: pd.DataFrame | None,
    df_material: pd.DataFrame | None,
    df_tools: pd.DataFrame | None,
    df_wydajnosc: pd.DataFrame | None,
    df_maszyny: pd.DataFrame | None,
    rates: dict,
    warns: list,
) -> pd.DataFrame | None:
    """
    Build the main 'prekalkulacja' DataFrame joining all sources.
    Returns DataFrame or None on critical failure.
    """
    if result is None:
        warns.append("Brak danych Postkalkulacji. Załaduj i oblicz Postkalkulację.")
        return None

    df_prof = result["df_prof"].copy()

    # ── Base columns from Profitability ──────────────────────────────────────
    BASE_COLS = [
        "Numer", "Klient ID", "Klient", "Zamówienie",
        "Zlecenie produkcyjne", "Lewy 10",
        "Opakowania zbiorcze [24]", "Klej [17]", "Lakiery [20]",
        "Kliki final", "Prepress costs", "Offset inks", "Płyta offsetowa",
        "Other Materials", "Data faktury", "Sales Value", "Zamawiana ilość",
    ]
    pk = pd.DataFrame(index=df_prof.index)
    for col in BASE_COLS:
        found = fcol(df_prof, col, col.replace("[", "").replace("]", "").strip())
        pk[col] = df_prof[found].values if found else None

    # Rename to clean names
    RENAMES = {
        "Opakowania zbiorcze [24]": "Opakowania zbiorcze",
        "Klej [17]": "Klej",
        "Lakiery [20]": "Lakiery",
        "Kliki final": "Pliki final",
        "Prepress costs": "Prepress",
        "Płyta offsetowa": "Płyty offset",
    }
    pk = pk.rename(columns=RENAMES)

    NUM_COLS = ["Opakowania zbiorcze", "Klej", "Lakiery", "Pliki final",
                "Prepress", "Offset inks", "Płyty offset", "Other Materials",
                "Sales Value", "Zamawiana ilość"]
    for c in NUM_COLS:
        if c in pk.columns:
            pk[c] = pd.to_numeric(pk[c], errors="coerce").fillna(0)

    pk["Zamawiana ilość z faktury"] = pk.get("Zamawiana ilość", pd.Series(0, index=pk.index))

    # ── Join Orders ───────────────────────────────────────────────────────────
    if df_orders is not None:
        nl_c = fcol(df_orders, "Numer-Linia", "Numer Linia", "Numer_Linia")
        wy_c = fcol(df_orders, "Wykrojnik")
        fmt_c = fcol(df_orders, "Format")
        kl_c = fcol(df_orders, "Klient")
        op_c = fcol(df_orders, "Opis produktu")
        tp_c = fcol(df_orders, "Typ produktu")
        qty_o_c = fcol(df_orders, "Zamawiana ilość")
        nzk_c = fcol(df_orders, "Numer Zam. Klineta", "Numer Zam. Klienta")

        if nl_c:
            rename_map = {nl_c: "_ord_nl"}
            if wy_c:
                rename_map[wy_c] = "Wykrojnik"
            if fmt_c:
                rename_map[fmt_c] = "Format"
            if kl_c:
                rename_map[kl_c] = "Klient z Orders"
            if op_c:
                rename_map[op_c] = "Opis produktu"
            if tp_c:
                rename_map[tp_c] = "Typ produktu"
            if qty_o_c:
                rename_map[qty_o_c] = "Zamawiana ilość (Orders)"
            if nzk_c:
                rename_map[nzk_c] = "Numer Zam. Klineta"

            df_ord2 = df_orders.rename(columns=rename_map)
            keep = ["_ord_nl"] + [v for v in rename_map.values() if v != "_ord_nl"
                                   and v in df_ord2.columns]
            df_ord2 = df_ord2[keep].drop_duplicates("_ord_nl")
            pk["_lewy10"] = pk["Lewy 10"].astype(str).str.strip()
            df_ord2["_ord_nl"] = df_ord2["_ord_nl"].astype(str).str.strip()
            pk = pk.merge(df_ord2, left_on="_lewy10", right_on="_ord_nl", how="left")
            pk.drop(columns=["_lewy10", "_ord_nl"], errors="ignore", inplace=True)
        else:
            warns.append("Orders: brak kolumny 'Numer-Linia' — nie można złączyć.")

    # ── Join Tektura ──────────────────────────────────────────────────────────
    if df_tektura is not None:
        jn_c = fcol(df_tektura, "job_name")
        mx_c = fcol(df_tektura, "mindex")
        nm_c = fcol(df_tektura, "name")
        cl_c = fcol(df_tektura, "client_name")
        vq_c = fcol(df_tektura, "(m.value/ m.qty)", "m.value/ m.qty", "m.value/m.qty")

        if jn_c:
            tek_cols = {jn_c: "_tek_jn"}
            if mx_c:
                tek_cols[mx_c] = "mindex tektura"
            if nm_c:
                tek_cols[nm_c] = "name tektura"
            if cl_c:
                tek_cols[cl_c] = "client_name tektura"
            if vq_c:
                tek_cols[vq_c] = "Cena tektury (m.value/m.qty)"
            df_tek2 = df_tektura.rename(columns=tek_cols)
            sel = ["_tek_jn"] + [v for v in tek_cols.values() if v != "_tek_jn"]
            df_tek2 = df_tek2[[c for c in sel if c in df_tek2.columns]].drop_duplicates("_tek_jn")
            pk["_zp"] = pk["Zlecenie produkcyjne"].astype(str).str.strip()
            df_tek2["_tek_jn"] = df_tek2["_tek_jn"].astype(str).str.strip()
            pk = pk.merge(df_tek2, left_on="_zp", right_on="_tek_jn", how="left")
            pk.drop(columns=["_zp", "_tek_jn"], errors="ignore", inplace=True)
        else:
            warns.append("Tektura: brak kolumny 'job_name'.")
    else:
        pk["Cena tektury (m.value/m.qty)"] = 0.0

    val_col = "Cena tektury (m.value/m.qty)"
    if val_col not in pk.columns:
        pk[val_col] = 0.0
    pk[val_col] = pd.to_numeric(pk[val_col], errors="coerce").fillna(0)

    # ── Join Tools → Nesting ──────────────────────────────────────────────────
    if df_tools is not None and "Wykrojnik" in pk.columns:
        tl_nm = fcol(df_tools, "Nazwa narzędzia")
        tl_ne = fcol(df_tools, "Ilość użytków wykrojnika / Nesting",
                     "Ilość użytków wykrojnika/Nesting")
        if tl_nm and tl_ne:
            df_tl2 = df_tools[[tl_nm, tl_ne]].rename(
                columns={tl_nm: "_tl_nm", tl_ne: "Nesting"}
            ).drop_duplicates("_tl_nm")
            df_tl2["Nesting"] = pd.to_numeric(df_tl2["Nesting"], errors="coerce")
            pk["_wyk"] = pk["Wykrojnik"].astype(str).str.strip()
            df_tl2["_tl_nm"] = df_tl2["_tl_nm"].astype(str).str.strip()
            pk = pk.merge(df_tl2, left_on="_wyk", right_on="_tl_nm", how="left")
            pk.drop(columns=["_wyk", "_tl_nm"], errors="ignore", inplace=True)
        else:
            pk["Nesting"] = None
    else:
        pk["Nesting"] = None

    pk["Nesting"] = pd.to_numeric(pk.get("Nesting"), errors="coerce")

    # ── Core quantity calculations ────────────────────────────────────────────
    qty = pk["Zamawiana ilość"].fillna(0).astype(float)
    nesting = pk["Nesting"].fillna(0).astype(float)

    def safe_div(a, b):
        return np.where(b != 0, a / b, 0.0)

    pk["Liczba arkuszy"] = safe_div(qty.values, nesting.values)
    pk["Liczba arkuszy do produkcji"] = pk["Liczba arkuszy"] * 1.1
    pk["Koszt tektury"] = pk["Liczba arkuszy"] * pk[val_col].fillna(0)

    # ── Join Material Service (Gilotyna) ─────────────────────────────────────
    pk["liczba cięć"] = 0.0
    if df_material is not None:
        mx_m = fcol(df_material, "mindex")
        lc_m = fcol(df_material, "liczba_cięć", "Liczba cięć")
        if not mx_m:
            mx_m = fcol(df_material, "Index")
        if mx_m and lc_m:
            df_mat2 = (
                df_material[[mx_m, lc_m]]
                .rename(columns={mx_m: "_mat_mx", lc_m: "_mat_lc"})
                .dropna(subset=["_mat_lc"])
            )
            df_mat2["_mat_lc"] = pd.to_numeric(df_mat2["_mat_lc"], errors="coerce")
            df_mat2 = df_mat2.groupby("_mat_mx")["_mat_lc"].mean().reset_index()
            pk_mx = pk.get("mindex tektura", pk["Zlecenie produkcyjne"]).astype(str).str.strip()
            df_mat2["_mat_mx"] = df_mat2["_mat_mx"].astype(str).str.strip()
            pk["_pk_mx"] = pk_mx
            pk = pk.merge(df_mat2, left_on="_pk_mx", right_on="_mat_mx", how="left")
            pk.drop(columns=["_pk_mx", "_mat_mx"], errors="ignore", inplace=True)
            pk["liczba cięć"] = pd.to_numeric(pk.get("_mat_lc"), errors="coerce").fillna(0)
            pk.drop(columns=["_mat_lc"], errors="ignore", inplace=True)

    # ── Gilotyna cost ─────────────────────────────────────────────────────────
    wy_map = wydajnosc_as_dict(df_wydajnosc) if df_wydajnosc is not None else {}
    gilotyna_rate = 0.0
    gilotyna_wy = 0.0
    for nm, wr in wy_map.items():
        if "gilotyna" in nm.lower():
            gilotyna_rate = sn(wr.get("Stawka rbg", 0))
            gilotyna_wy = sn(wr.get("Wydajność", 0))
            break
    if gilotyna_rate == 0:
        gilotyna_rate = rates.get("Gilotyna", 65.69)

    ark_arr = pk["Liczba arkuszy"].fillna(0).astype(float).values
    lc_arr = pk["liczba cięć"].fillna(0).astype(float).values
    if gilotyna_wy > 0:
        pk["Koszt gilotyny"] = np.where(
            lc_arr > 0,
            gilotyna_rate * (ark_arr / np.where(lc_arr > 0, lc_arr, 1)) / gilotyna_wy,
            0.0,
        )
    else:
        pk["Koszt gilotyny"] = 0.0

    # ── Machine costs from maszyny ────────────────────────────────────────────
    machine_cost_cols: list[str] = []
    if df_maszyny is not None and df_wydajnosc is not None:
        nzp_m = fcol(df_maszyny, "Numer zlecenia produkcyjnego")
        nm_m = fcol(df_maszyny, "Nazwa maszyny")
        if nzp_m and nm_m:
            unique_machines = df_maszyny[nm_m].dropna().unique()

            # Build lookup: maszyna → {zp_key: True}
            for mach in unique_machines:
                mach_s = str(mach).strip()
                col_nm = f"Koszt {mach_s}"
                wr = wy_map.get(mach_s, {})
                stawka = sn(wr.get("Stawka rbg", 0)) if wr else rate_for_machine(mach_s, rates)
                wydajnosc_m = sn(wr.get("Wydajność", 0)) if wr else 0
                miara = str(wr.get("Miara", "")).strip().lower() if wr else ""

                df_m_filt = df_maszyny[df_maszyny[nm_m].astype(str).str.strip() == mach_s]
                # Set of ZP keys associated with this machine
                zp_set = set(df_m_filt[nzp_m].astype(str).str.strip().tolist())

                if wydajnosc_m <= 0 or stawka <= 0:
                    pk[col_nm] = 0.0
                    machine_cost_cols.append(col_nm)
                    warns.append(f"⚠️ Maszyna '{mach_s}': brak stawki lub wydajności → koszt = 0.")
                    continue

                def _cost(row, _zp_set=zp_set, _stawka=stawka,
                          _wy=wydajnosc_m, _miara=miara):
                    zp = str(row.get("Zlecenie produkcyjne", "")).strip()
                    matched = next(
                        (k for k in _zp_set if zp in k or k.startswith(zp)), None
                    )
                    if matched is None:
                        return 0.0
                    ark = sn(row.get("Liczba arkuszy", 0))
                    qty_row = sn(row.get("Zamawiana ilość", 0))
                    if "ark" in _miara or _miara == "":
                        return _stawka * ark / _wy
                    else:
                        return _stawka * (qty_row * 1.05) / _wy

                pk[col_nm] = pk.apply(_cost, axis=1)
                machine_cost_cols.append(col_nm)

    # ── Total DL ─────────────────────────────────────────────────────────────
    dl_cols = machine_cost_cols + ["Koszt gilotyny"]
    for c in dl_cols:
        if c not in pk.columns:
            pk[c] = 0.0
        pk[c] = pd.to_numeric(pk[c], errors="coerce").fillna(0)
    pk["Total DL"] = pk[dl_cols].sum(axis=1)

    # ── Total Materials Cost ──────────────────────────────────────────────────
    MAT_COLS = [
        "Koszt tektury", "Pliki final", "Offset inks",
        "Płyty offset", "Opakowania zbiorcze", "Klej", "Lakiery", "Other Materials",
    ]
    for c in MAT_COLS:
        if c not in pk.columns:
            pk[c] = 0.0
        pk[c] = pd.to_numeric(pk[c], errors="coerce").fillna(0)
    pk["Total Materials Cost"] = pk[MAT_COLS].sum(axis=1)

    # ── TPM, CM, % ───────────────────────────────────────────────────────────
    sv = pk["Sales Value"].fillna(0).astype(float)
    pk["TPM"] = sv - pk["Total Materials Cost"]
    pk["CM"] = sv - pk["Total Materials Cost"] - pk["Total DL"]
    pk["TPM%"] = np.where(sv != 0, pk["TPM"] / sv, 0.0)
    pk["CM%"] = np.where(sv != 0, pk["CM"] / sv, 0.0)

    # ── Month ─────────────────────────────────────────────────────────────────
    pk["Data faktury"] = pd.to_datetime(pk["Data faktury"], errors="coerce")
    pk["Miesiąc faktury"] = pk["Data faktury"].dt.strftime("%Y-%m")

    # Remove stray helper cols
    pk = pk[[c for c in pk.columns if not c.startswith("_")]]

    return pk
