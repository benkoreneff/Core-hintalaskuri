# app/utils.py

import re
import pandas as pd


# --- Exclusion list helpers ---------------------------------------------------

def normalize_business_id(value) -> str:
    """'1234567-8' / 'FI12345678' → '12345678' (digits only)."""
    if pd.isna(value):
        return ""
    s = str(value).strip().upper()
    s = re.sub(r"^FI", "", s)          # drop FI VAT prefix if present
    s = re.sub(r"\D", "", s)           # keep digits only
    return s


def normalize_name(value) -> str:
    """Lowercase, collapse whitespace; robust string match for company names."""
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().lower().split())


def find_col(df: pd.DataFrame, candidates) -> str | None:
    """
    Return the original column name in df that matches any of 'candidates'
    (case/spacing/diacritics insensitive).
    """
    normalized = {re.sub(r"[^a-z0-9]+", "", c.lower()): c for c in df.columns}
    for cand in candidates:
        key = re.sub(r"[^a-z0-9]+", "", cand.lower())
        if key in normalized:
            return normalized[key]
    return None

