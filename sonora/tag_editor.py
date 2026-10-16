from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from mutagen import File as MutagenFile


TAG_KEYS = {
    "title": "title",
    "artist": "artist",
    "album_artist": "albumartist",
    "album": "album",
    "genre": "genre",
    "composer": "composer",
    "year": "date",
    "track_number": "tracknumber",
    "disc_number": "discnumber",
}


def backup_path(path: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = path.with_name(f"{path.name}.sonora-{timestamp}.bak")
    suffix = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.sonora-{timestamp}-{suffix}.bak")
        suffix += 1
    return candidate


def write_tags(path: str | Path, values: dict[str, str]) -> Path:
    """Back up an audio file and write the supplied Mutagen easy tag values."""
    source = Path(path)
    audio = MutagenFile(source, easy=True)
    if audio is None:
        raise ValueError("Sonora could not read this audio file's tags.")
    backup = backup_path(source)
    shutil.copy2(source, backup)
    try:
        if audio.tags is None:
            audio.add_tags()
        for field, value in values.items():
            key = TAG_KEYS[field]
            clean = str(value).strip()
            if clean:
                audio[key] = [clean]
            elif key in audio:
                del audio[key]
        audio.save()
    except Exception:
        shutil.copy2(backup, source)
        raise
    return backup

