import re


ROLE_PATTERN = re.compile(
    r"\b(analyst|analytics|research|underwrit\w*|valuation\w*|acquisition\w*|"
    r"asset management|portfolio management|capital markets|real estate finance|"
    r"market intelligence|investment analyst)\b",
    re.IGNORECASE,
)
EXCLUDE_PATTERN = re.compile(
    r"\b(software|engineering|help desk|digital workplace|human resources|"
    r"marketing|security operations|sales development)\b",
    re.IGNORECASE,
)


def is_in_role(title: str) -> bool:
    """Return whether a title is relevant to a CRE analyst watchlist."""

    title = title or ""
    return bool(ROLE_PATTERN.search(title) and not EXCLUDE_PATTERN.search(title))
