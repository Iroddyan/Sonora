from __future__ import annotations

import re


_BRACKETED_NOISE = re.compile(
    r"\s*[\[(]\s*(?:official\s+(?:music\s+)?vid[eé]o|official\s+audio|"
    r"music\s+vid[eé]o|lyric\s+vid[eé]o|lyrics?|visuali[sz]er|4k|1080p|720p|hd)\s*[\])]",
    re.IGNORECASE,
)
_TRAILING_NOISE = re.compile(
    r"\s*[-–—|]\s*(?:official\s+(?:music\s+)?vid[eé]o|official\s+audio|"
    r"music\s+vid[eé]o|lyric\s+vid[eé]o|lyrics?|visuali[sz]er|4k|1080p|720p|hd)\s*$",
    re.IGNORECASE,
)


def clean_title_metadata(title: str, artist: str = "") -> dict[str, str]:
    """Suggest conservative title/artist cleanup without changing the input."""
    before_title = " ".join((title or "").split())
    clean_title = _BRACKETED_NOISE.sub("", before_title)
    clean_title = _TRAILING_NOISE.sub("", clean_title)
    clean_title = re.sub(r"\s+", " ", clean_title).strip(" -–—|\t")
    clean_artist = " ".join((artist or "").split())

    if clean_artist:
        prefix = re.match(r"^(.+?)\s+[-–—]\s+(.+)$", clean_title)
        if prefix and prefix.group(1).casefold() == clean_artist.casefold():
            clean_title = prefix.group(2).strip()
    else:
        prefix = re.match(r"^(.+?)\s+[-–—]\s+(.+)$", clean_title)
        if prefix:
            clean_artist, clean_title = prefix.group(1).strip(), prefix.group(2).strip()

    changes = {}
    if clean_title and clean_title != before_title:
        changes["title"] = clean_title
    if clean_artist and clean_artist != (artist or "").strip():
        changes["artist"] = clean_artist
    return changes
