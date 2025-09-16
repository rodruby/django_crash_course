"""
csv_processing.py

Contains robust functions to parse uploaded CSV/XLSX files into pandas DataFrames,
clean columns, compute price_per_sf, perform yearly/monthly aggregations,
compute month-over-month percent changes, and derive suggested monthly time adjustments.

Functions:
- parse_and_clean_file(uploaded_file) -> (df, rows_excluded_count)
- analyze_sales_dataframe(df, n_last_months=12) -> result_dict
"""

from typing import Tuple, Dict, Any
import pandas as pd
import numpy as np
from io import BytesIO

EXPECTED_COLUMNS = [
    "MLSNumber", "StreetNumberNumeric", "StreetName", "City", "CDOM", "ListPrice",
    "CurrentPrice", "ClosePrice", "PendingDate", "CloseDate", "SqFtTotal",
    "SqFtLivArea", "View", "WaterView"
]

def normalize_columns(cols):
    """Return a mapping from normalized (lower) to original expected name if matches."""
    mapping = {}
    lowers = {c.lower(): c for c in EXPECTED_COLUMNS}
    for col in cols:
        key = col.strip().lower()
        if key in lowers:
            mapping[col] = lowers[key]
    return mapping

def try_read_file(uploaded_file) -> pd.DataFrame:
    """Attempt to read uploaded file (csv or excel). Try multiple encodings for CSV."""
    name = uploaded_file.name.lower()
    uploaded_file.seek(0)
    if name.endswith('.csv'):
        # Try to read normally, then with utf-16 and latin-1
        for enc in (None, 'utf-8', 'utf-16', 'latin-1'):
            try:
                if enc:
                    df = pd.read_csv(uploaded_file, encoding=enc)
                else:
                    # first attempt without specifying encoding
                    df = pd.read_csv(uploaded_file)
                uploaded_file.seek(0)
                return df
            except Exception:
                uploaded_file.seek(0)
                continue
        raise ValueError("Unable to parse CSV - try saving as CSV (UTF-8) or upload as Excel.")
    elif name.endswith(('.xls', '.xlsx')):
        try:
            df = pd.read_excel(uploaded_file)
            uploaded_file.seek(0)
            return df
        except Exception as e:
            raise ValueError(f"Unable to parse Excel file: {e}")
    else:
        raise ValueError("Unsupported file type. Upload .csv, .xls, or .xlsx")

def parse_and_clean_file(uploaded_file) -> Tuple[pd.DataFrame, int]:
    """
    Parse and clean file. Returns (cleaned_df, rows_excluded_count).
    - Normalizes column names to expected set
    - Coerces numeric fields (prices, sq ft)
    - Parses dates, drops rows missing ClosePrice or CloseDate
    - Computes price_per_sf column
    """
    df = try_read_file(uploaded_file)

    # Normalize columns: map case-insensitive names to expected exact names
    col_map = {}
    for c in df.columns:
        lc = c.strip().lower()
        for expected in EXPECTED_COLUMNS:
            if lc == expected.lower():
                col_map[c] = expected
                break
    df = df.rename(columns=col_map)

    # Validate at least the core columns exist
    core = ['ClosePrice', 'CloseDate', 'SqFtTotal', 'SqFtLivArea']
    missing = [c for c in core if c not in df.columns]
    if missing:
        # If ClosePrice or CloseDate missing, try to find case-insensitive variants
        raise ValueError(f"Missing required column(s): {', '.join(missing)}")

    # Clean price columns: remove $ and commas then convert to numeric
    price_cols = ['ListPrice', 'CurrentPrice', 'ClosePrice']
    for col in price_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).replace(r'[\$,]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Clean sqft columns
    sqft_cols = ['SqFtTotal', 'SqFtLivArea']
    for col in sqft_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Parse dates
    df['CloseDate'] = pd.to_datetime(df['CloseDate'], errors='coerce')

    initial_rows = len(df)
    # Drop rows missing ClosePrice or CloseDate
    df = df[df['ClosePrice'].notna()]
    df = df[df['CloseDate'].notna()]
    rows_excluded = initial_rows - len(df)

    # Compute price_per_sf using rule: SqFtLivArea if >0 else SqFtTotal
    def compute_pps(row):
        price = row.get('ClosePrice', np.nan)
        sqft_l = row.get('SqFtLivArea', np.nan)
        sqft_t = row.get('SqFtTotal', np.nan)
        sqft = None
        if pd.notna(sqft_l) and sqft_l > 0:
            sqft = sqft_l
        elif pd.notna(sqft_t) and sqft_t > 0:
            sqft = sqft_t
        if pd.isna(price) or sqft is None or sqft == 0:
            return np.nan
        return price / sqft

    df['price_per_sf'] = df.apply(compute_pps, axis=1)

    # Year / Year-Month columns
    df['year'] = df['CloseDate'].dt.year
    df['year_month'] = df['CloseDate'].dt.to_period('M').astype(str)  # 'YYYY-MM'

    return df, rows_excluded

def analyze_sales_dataframe(df: pd.DataFrame, n_last_months: int = 12) -> Dict[str, Any]:
    """
    Analyze df and return structured dict:
    - monthly_table: list of dicts {year_month, mean_close, median_close, mean_pps, median_pps, n}
    - yearly_table: list of dicts {year, mean_close, median_close, mean_pps, median_pps, n}
    - time_adjustments: median_last_n_months, mean_last_n_months, regression_monthly_pct, n_used
    - rows_processed, rows_excluded
    """
    # Aggregate monthly
    monthly = (
        df.groupby('year_month')
        .agg(mean_close=('ClosePrice', 'mean'),
             median_close=('ClosePrice', 'median'),
             mean_pps=('price_per_sf', 'mean'),
             median_pps=('price_per_sf', 'median'),
             n=('ClosePrice', 'count'))
        .reset_index()
        .sort_values('year_month')
    )

    yearly = (
        df.groupby('year')
        .agg(mean_close=('ClosePrice', 'mean'),
             median_close=('ClosePrice', 'median'),
             mean_pps=('price_per_sf', 'mean'),
             median_pps=('price_per_sf', 'median'),
             n=('ClosePrice', 'count'))
        .reset_index()
        .sort_values('year')
    )

    # Compute month-over-month percent changes for median_pps (and median_close)
    monthly['median_pps_pct_change'] = monthly['median_pps'].pct_change()
    monthly['median_close_pct_change'] = monthly['median_close'].pct_change()
    monthly['mean_pps_pct_change'] = monthly['mean_pps'].pct_change()
    monthly['mean_close_pct_change'] = monthly['mean_close'].pct_change()

    # Choose last N months of median_pps_pct_change (dropna)
    recent = monthly['median_pps_pct_change'].dropna().tail(n_last_months)
    n_used = len(recent)

    median_last_n = float(recent.median()) if n_used > 0 else 0.0
    mean_last_n = float(recent.mean()) if n_used > 0 else 0.0

    # Regression-based monthly pct: regression of median_pps on time index
    # Use only months with non-null median_pps
    med_pps_nonnull = monthly.dropna(subset=['median_pps']).reset_index(drop=True)
    regression_monthly_pct = 0.0
    if len(med_pps_nonnull) >= 2:
        # Create numeric time variable
        med_pps_nonnull['time_idx'] = np.arange(len(med_pps_nonnull))
        # Linear regression (slope) on median_pps
        slope, intercept = np.polyfit(med_pps_nonnull['time_idx'], med_pps_nonnull['median_pps'], 1)
        # Convert slope to monthly percent relative to mean price
        mean_price = med_pps_nonnull['median_pps'].mean()
        if mean_price and mean_price != 0:
            regression_monthly_pct = float(slope / mean_price)
        else:
            regression_monthly_pct = 0.0

    # Prepare JSON-serializable outputs - replace NaN values with None for JSON serialization
    monthly_table = monthly.replace({np.nan: None}).to_dict(orient='records')
    yearly_table = yearly.replace({np.nan: None}).to_dict(orient='records')

    results = {
        "monthly_table": monthly_table,
        "yearly_table": yearly_table,
        "time_adjustments": {
            "median_last_n_months": median_last_n,
            "mean_last_n_months": mean_last_n,
            "regression_monthly_pct": regression_monthly_pct,
            "n_used": n_used
        },
        "rows_processed": int(len(df)),
        # rows_excluded should be provided by parse stage if needed
    }
    return results
