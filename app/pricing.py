import pandas as pd


def apply_margin(
        df: pd.DataFrame,
        base_col: str,
        margin_pct: float,
        new_col: str = None
) -> pd.DataFrame:
    """
    Given a DataFrame with a numeric column `base_col` (e.g. 'Avg3Mo'),
    compute fixed price = base_col * (1 + margin_pct/100).
    Adds a new column `new_col` (defaults to '{base_col}_With{margin_pct:.0f}Pct').
    """
    df = df.copy()
    if new_col is None:
        new_col = f"{base_col}_With{margin_pct:.0f}Pct"
    df[new_col] = df[base_col] * (1 + margin_pct / 100.0)
    return df


def add_fixed_price_suggestions(
        df: pd.DataFrame,
        margins: dict
) -> pd.DataFrame:
    """
    For each entry in `margins`, where keys are average-column names
    (e.g. 'Avg3Mo', 'Avg12Mo') and values are margin percentages,
    apply apply_margin and return a DataFrame with all new suggestion cols.

    Example:
        margins = {'Avg3Mo': 15, 'Avg12Mo': 10}
    """
    df = df.copy()
    for avg_col, pct in margins.items():
        df = apply_margin(df, base_col=avg_col, margin_pct=pct)
    return df


if __name__ == "__main__":
    # smoke test using analytics module
    from parser import load_data, clean_dataframe
    from analytics import compute_company_averages

    # load & clean
    path = '../data/netvisor_procountor_2024_2025.xlsx'
    raw = load_data(path)
    clean = clean_dataframe(raw)
    stats = compute_company_averages(clean)

    # add 15% margin on 3-month avg, 10% margin on 12-month avg
    suggestions = add_fixed_price_suggestions(stats, {'Avg3Mo': 15, 'Avg12Mo': 10})

    print(suggestions.head())
