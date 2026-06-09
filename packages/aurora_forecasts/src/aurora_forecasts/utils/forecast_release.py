import re
from dataclasses import dataclass
from typing import Optional, Dict, Iterable


# =========================
# Public data structure
# =========================

@dataclass(frozen=True)
class ReleaseInfo:
    quarter: Optional[int]   # 1..4
    month: Optional[int]     # 1..12
    month_str: Optional[str] # "Jan", "Apr", etc.
    year: Optional[int]      # 4-digit year (e.g. 2024)


# =========================
# Constants & regex
# =========================

_MONTH_MAP: Dict[str, int] = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_MONTH_QUARTER_MAP: Dict[int, int] = {
    1: 1, 2: 1, 3: 1,
    4: 2, 5: 2, 6: 2,
    7: 3, 8: 3, 9: 3,
    10: 4, 11: 4, 12: 4,
}

_QUARTER_MONTH_MAP: Dict[int, int] = {
    1: 1,
    2: 4,
    3: 7,
    4: 10,
}

_QUARTER_MONTH_STR_MAP: Dict[int, str] = {
    1: "Jan",
    2: "Apr",
    3: "Jul",
    4: "Oct",
}

# Quarter formats: "Q1 26", "Q1-2026", "Q1/26"
_Q_RE = re.compile(r"\bQ([1-4])\s*[-_/]?\s*(\d{2,4})\b", re.IGNORECASE)

# Quarter formats with year first: "2026 Q1", "2026Q1", "26 Q1"
_YEAR_Q_RE = re.compile(r"\b(\d{2,4})\s*[-_/]?\s*Q([1-4])\b", re.IGNORECASE)

# Month formats:
# - "Jan24", "Jan 24", "Jan  2022", "April 21", "Oct-2020", "Jul_24"
# NOTE: no \b after month token so "Jan24" works
_MONTH_RE = re.compile(
    r"("
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
    r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|"
    r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    r")\.?\s*[-_/]?\s*(\d{2,4})\b",
    re.IGNORECASE
)


# =========================
# Helpers
# =========================

def _normalize(s: str) -> str:
    """Normalises an input string for reliable regex matching.

    Inserts a space between a lowercase letter and a month name when they
    are run together (e.g. ``"Q1Jan26"`` → ``"Q1 Jan26"``), then collapses
    all internal whitespace runs to a single space and strips leading/trailing
    whitespace.

    Args:
        s: Raw forecast name string. ``None`` is treated as an empty string.

    Returns:
        Normalised string ready for pattern matching.
    """
    s = "" if s is None else str(s)

    # Fix missing space before month names only
    s = re.sub(
        r"([a-z])("
        r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
        r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|"
        r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
        r")",
        r"\1 \2",
        s,
        flags=re.IGNORECASE,
    )

    # Normalize whitespace
    return re.sub(r"\s+", " ", s.strip())


def _year_2_to_4(y: int, pivot: int = 50) -> int:
    """Expands a 2-digit year to a 4-digit year using a pivot value.

    Args:
        y: Year value to expand. Values already >= 100 are returned unchanged.
        pivot: Values below ``pivot`` map to 2000+; values >= ``pivot``
            map to 1900+. Defaults to 50, so 00–49 → 2000–2049 and
            50–99 → 1950–1999.

    Returns:
        4-digit integer year.
    """
    if y < 100:
        return 2000 + y if y < pivot else 1900 + y
    return y


# =========================
# Public API
# =========================

def parse_release_info(name: str) -> ReleaseInfo:
    """Parses quarter, month, and year from a forecast release name string.

    Tries patterns in priority order:

    1. Explicit quarter-first tokens: ``"Q1 26"``, ``"Q3 2021"``, ``"Q1-2026"``.
    2. Year-first quarter tokens: ``"2026Q1"``, ``"2026 Q1"``, ``"26 Q1"``.
    3. Month + year tokens: ``"Jan24"``, ``"Jan 2024"``, ``"April 21"``,
       ``"Oct-2020"``.

    Args:
        name: Forecast name string to parse (e.g. ``"Aurora Q1 26 Central"``).

    Returns:
        :class:`ReleaseInfo` with ``quarter``, ``month``, ``month_str``, and
        ``year`` populated.

    Raises:
        ValueError: If no recognisable quarter or month+year pattern is found
            in ``name``.
    """
    # Normalize input to a consistent form so regex matching is reliable.
    s = _normalize(name)

    # Attempt to parse explicit quarter-first formats like "Q1 26".
    m = _Q_RE.search(s)
    if m:
        q = int(m.group(1))
        y = _year_2_to_4(int(m.group(2)))
        quarter_month = _QUARTER_MONTH_MAP[q]
        month_str = _QUARTER_MONTH_STR_MAP[q]
        return ReleaseInfo(quarter=q, month=quarter_month, month_str=month_str, year=y)

    # Attempt to parse formats where the year comes before the quarter.
    m = _YEAR_Q_RE.search(s)
    if m:
        y = _year_2_to_4(int(m.group(1)))
        q = int(m.group(2))
        quarter_month = _QUARTER_MONTH_MAP[q]
        month_str = _QUARTER_MONTH_STR_MAP[q]
        return ReleaseInfo(quarter=q, month=quarter_month, month_str=month_str, year=y)

    # Fall back to month+year formats such as "Jan24".
    m = _MONTH_RE.search(s)
    if m:
        mon_token = m.group(1).lower()
        month = _MONTH_MAP[mon_token]
        y = _year_2_to_4(int(m.group(2)))
        q = _MONTH_QUARTER_MAP[month]
        month_str = _QUARTER_MONTH_STR_MAP[q]
        return ReleaseInfo(quarter=q, month=month, month_str=month_str, year=y)

    raise ValueError(f"Could not parse release info from '{name}'")


def parse_many(names: Iterable[str]) -> Dict[str, ReleaseInfo]:
    """Parses release info from an iterable of forecast name strings.

    Args:
        names: Iterable of forecast name strings to parse.

    Returns:
        Dictionary mapping each name to its parsed :class:`ReleaseInfo`.

    Raises:
        ValueError: If any name cannot be parsed (propagated from
            :func:`parse_release_info`).
    """
    return {n: parse_release_info(n) for n in names}


def parse_release_info_safe(name: str) -> ReleaseInfo:
    """Parses release info from a forecast name, re-raising on failure.

    Wraps :func:`parse_release_info` with a consistent ``ValueError`` message,
    making it suitable for use in pandas ``apply`` pipelines where a uniform
    exception type is expected.

    Args:
        name: Forecast name string to parse.

    Returns:
        :class:`ReleaseInfo` with ``quarter``, ``month``, ``month_str``, and
        ``year`` populated.

    Raises:
        ValueError: If the name cannot be parsed.
    """
    try:
        return parse_release_info(name)
    except Exception:
        raise ValueError(f"Could not parse release info from '{name}'")
