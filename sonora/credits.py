from __future__ import annotations

import re
import unicodedata


SEPARATOR_PATTERN = re.compile(r"\s*(?:;|,|\s+feat(?:uring)?\.?\s+|\s+ft\.?\s+|\s+&\s+|\s+x\s+)\s*", re.IGNORECASE)
DEFAULT_ARTIST_EXCEPTIONS = (
    "Tyler, The Creator",
    "Earth, Wind & Fire",
    "AC/DC",
)


def normalize_name(value: str) -> str:
    """Return a stable Unicode and case-insensitive key for a library name."""
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def split_artist_credits(values, exceptions=()) -> tuple[str, list[str]]:
    """Split a tag into its primary and featured artists without breaking exceptions.

    Mutagen's multi-value tags are preferred: each supplied value is already an
    explicit artist credit. A single combined value is parsed using common
    separators, while exact exception names are temporarily protected.
    """
    if values is None:
        raw_values = []
    elif isinstance(values, str):
        raw_values = [values]
    else:
        raw_values = [str(value) for value in values if value is not None]
    cleaned = [value.strip() for value in raw_values if value and value.strip()]
    if not cleaned:
        return "", []

    if len(cleaned) > 1:
        credits = _unique(cleaned)
    else:
        text = cleaned[0]
        protected: dict[str, str] = {}
        exception_names = sorted(set(DEFAULT_ARTIST_EXCEPTIONS) | set(exceptions), key=len, reverse=True)
        for index, name in enumerate(exception_names):
            if not name:
                continue
            token = f"\uFFF0{index}\uFFF1"
            pattern = re.compile(re.escape(name), re.IGNORECASE)
            text, count = pattern.subn(token, text)
            if count:
                protected[token] = name
        credits = []
        for part in SEPARATOR_PATTERN.split(text):
            part = part.strip()
            for token, name in protected.items():
                part = part.replace(token, name)
            if part:
                credits.append(part)
        credits = _unique(credits)

    if not credits:
        return "", []
    return credits[0], credits[1:]


def _unique(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        value = value.strip()
        key = normalize_name(value)
        if value and key not in seen:
            result.append(value)
            seen.add(key)
    return result
