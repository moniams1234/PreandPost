"""session.py — Streamlit session-state helpers for persistent uploads."""
from __future__ import annotations

import streamlit as st


def upload_key(base_key: str) -> str:
    """Return an active Streamlit widget key that changes on every Wyczyść."""
    return f"{base_key}_{st.session_state.get('upload_clear_nonce', 0)}"


def store_uploaded_file(base_key: str, uploaded) -> None:
    """Persist uploaded file under a stable key so it survives tab switches."""
    if uploaded is not None:
        st.session_state[f"stored_{base_key}"] = uploaded


def current_file(base_key: str):
    """Return the currently active uploaded file for a logical uploader key."""
    active = st.session_state.get(upload_key(base_key))
    if active is not None:
        st.session_state[f"stored_{base_key}"] = active
        return active
    return st.session_state.get(f"stored_{base_key}")


def has_current_file(base_key: str) -> bool:
    return current_file(base_key) is not None
