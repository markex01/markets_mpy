"""Unit conversion utilities for Aurora forecast DataFrames."""

import pandas as pd

# Default conversion rules: (type, from_unit) → (to_unit, factor).
# Add entries here when Aurora introduces new unit variants for existing types.
DEFAULT_UNIT_CONVERSION_MAP: dict[tuple[str, str], tuple[str, float]] = {
    ("Capacity",   "GW"):  ("MW",  1000.0),
    ("Capacity",   "MW"):  ("MW",  1.0),    # already in target unit — no-op
    ("Generation", "TWh"): ("GWh", 1000.0),
    ("Generation", "GWh"): ("GWh", 1.0),   # already in target unit — no-op
}


def convert_units(
    df: pd.DataFrame,
    unit_conversion_map: dict[tuple[str, str], tuple[str, float]] | None = None,
) -> pd.DataFrame:
    """Convert the value and unit columns of an Aurora technology DataFrame.

    Applies unit conversions based on a ``(type, from_unit) → (to_unit, factor)``
    mapping. Rows whose ``(type, unit)`` pair is not present in the map are left
    unchanged.

    Args:
        df: DataFrame with at least ``type``, ``unit``, and ``value`` columns,
            as produced by the Aurora technology forecast pipeline.
        unit_conversion_map: Conversion rules mapping ``(type, from_unit)`` to
            ``(to_unit, factor)``. Defaults to ``DEFAULT_UNIT_CONVERSION_MAP``,
            which converts GW → MW and TWh → GWh.

    Returns:
        The same DataFrame with ``value`` scaled and ``unit`` updated in-place.

    Example:
        >>> convert_units(df_fil)
        >>> convert_units(df_fil, {("Capacity", "GW"): ("MW", 1000.0)})
    """
    if unit_conversion_map is None:
        unit_conversion_map = DEFAULT_UNIT_CONVERSION_MAP

    for (type_val, from_unit), (to_unit, factor) in unit_conversion_map.items():
        mask = (df["type"] == type_val) & (df["unit"] == from_unit)
        df.loc[mask, "value"] *= factor
        df.loc[mask, "unit"] = to_unit

    return df
