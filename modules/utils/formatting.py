"""formatting.py — column classification and number format helpers."""
from __future__ import annotations


def is_currency_col(name: str) -> bool:
    kw = [
        "wartość", "wartosc", "koszt", "sales", "tpm", "cm", "total",
        "prepress", "materials", "inks", "płyta", "kliki", "papier",
        "klej", "lak", "opak", "farby", "praca", "moje", "sprzedaż",
        "sprzedaz", "stawka", "rbg",
    ]
    n = name.lower()
    return any(k in n for k in kw)
