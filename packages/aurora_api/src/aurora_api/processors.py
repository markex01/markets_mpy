from __future__ import annotations

from typing import Any

import pandas as pd


def _extract_units(df: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    """Extracts the units row from a raw forecast DataFrame.

    The Aurora API returns a DataFrame whose first row contains unit labels
    for each column. This helper splits that row out so the caller can attach
    units to melted rows via a variable → unit mapping.

    Args:
        df: Raw forecast DataFrame where row 0 contains unit labels.

    Returns:
        A 2-tuple of:
            - units: dict mapping column name to its unit string.
            - df_clean: DataFrame with the units row removed and index reset.
    """
    units = df.iloc[0].to_dict()
    df_clean = df.iloc[1:].copy()
    df_clean.reset_index(drop=True, inplace=True)
    return units, df_clean


def _ensure_numeric_year(df: pd.DataFrame) -> pd.DataFrame:
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    return df


def _ensure_numeric_month(df: pd.DataFrame) -> pd.DataFrame:
    month_mapping = {
        "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
        "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
    }
    df["month"] = df["month"].map(month_mapping).astype("Int64")
    return df


def process_system_forecast(df: pd.DataFrame, resolution: str) -> pd.DataFrame:
    """Transforms a raw Aurora system forecast CSV into a long-format DataFrame.

    Handles three resolutions:

    - ``"1y"``: Renames ``Year`` → ``year``, melts all other columns into
      ``(year, variable, value, units)`` rows.
    - ``"1m"``: Renames ``Year`` → ``year`` and ``Month`` → ``month``, melts
      remaining columns into ``(year, month, variable, value, units)`` rows.
    - ``"1h"``: Uses the first column as ``datetime`` (parsed as datetime),
      melts remaining columns into ``(datetime, variable, value, units)`` rows.

    Args:
        df: Raw DataFrame as returned by the HTTP client, where the first row
            contains unit labels.
        resolution: Time resolution — ``"1y"``, ``"1m"``, or ``"1h"``.

    Returns:
        Long-format DataFrame with a ``units`` column. Returns an empty
        DataFrame for unrecognised resolutions.
    """
    units, df_clean = _extract_units(df)

    if resolution == "1y":
        df_clean.rename(columns={"Year": "year"}, inplace=True)
        df_long = df_clean.melt(id_vars="year", var_name="variable", value_name="value")
        df_long["units"] = df_long["variable"].map(units)
        return _ensure_numeric_year(df_long)

    if resolution == "1m":
        df_clean.rename(columns={"Year": "year", "Month": "month"}, inplace=True)
        df_long = df_clean.melt(
            id_vars=["year", "month"], var_name="variable", value_name="value"
        )
        df_long["units"] = df_long["variable"].map(units)
        df_long = _ensure_numeric_year(df_long)
        return _ensure_numeric_month(df_long)

    if resolution == "1h":
        datetime_col = df_clean.columns[0]
        df_clean.rename(columns={datetime_col: "datetime"}, inplace=True)
        df_clean["datetime"] = pd.to_datetime(df_clean["datetime"], errors="coerce")
        df_long = df_clean.melt(
            id_vars=["datetime"], var_name="variable", value_name="value"
        )
        df_long["units"] = df_long["variable"].map(units)
        return df_long

    return pd.DataFrame()


def process_technology_forecast(df: pd.DataFrame, resolution: str) -> pd.DataFrame:
    """Transforms a raw Aurora technology forecast CSV into a long-format DataFrame.

    Handles two resolutions:

    - ``"1y"``: Renames ``Year`` → ``year``, melts value columns into
      ``(year, Group, Subgroup, type, value, unit)`` rows.
    - ``"1m"``: Renames ``Year`` → ``year`` and ``Month`` → ``month``, melts
      value columns into ``(year, month, Group, Subgroup, type, value, unit)``
      rows.

    Args:
        df: Raw DataFrame as returned by the HTTP client, where the first row
            contains unit labels.
        resolution: Time resolution — ``"1y"`` or ``"1m"``.

    Returns:
        Long-format DataFrame with a ``unit`` column. Returns an empty
        DataFrame for unrecognised resolutions.
    """
    units, df_clean = _extract_units(df)

    if resolution == "1y":
        df_clean.rename(columns={"Year": "year"}, inplace=True)
        df_melted = df_clean.melt(
            id_vars=["year", "Group", "Subgroup"], var_name="type", value_name="value"
        )
        df_melted["unit"] = df_melted["type"].map(units)
        df_melted = _ensure_numeric_year(df_melted)
        df_melted.dropna(subset=["value"], inplace=True)
        df_melted.sort_values(by=["year", "Group", "Subgroup", "type"], inplace=True)
        return df_melted.reset_index(drop=True)

    if resolution == "1m":
        df_clean.rename(columns={"Year": "year", "Month": "month"}, inplace=True)
        df_melted = df_clean.melt(
            id_vars=["year", "month", "Group", "Subgroup"],
            var_name="type",
            value_name="value",
        )
        df_melted["unit"] = df_melted["type"].map(units)
        df_melted = _ensure_numeric_year(df_melted)
        df_melted = _ensure_numeric_month(df_melted)
        df_melted.dropna(subset=["value"], inplace=True)
        df_melted.sort_values(
            by=["year", "month", "Group", "Subgroup", "type"], inplace=True
        )
        return df_melted.reset_index(drop=True)

    return pd.DataFrame()
