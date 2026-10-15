from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Track:
    id: int
    path: str
    title: str
    artist: str
    album_artist: str
    album: str
    genre: str
    track_number: int
    disc_number: int
    year: int
    duration_ms: int
    artwork_path: str
    artwork_accent: str
    first_seen_at: str = ""
    size_bytes: int = 0
    modified_ms: int = 0
    missing: bool = False
    play_count: int = 0
    last_played_at: str = ""
    primary_artist: str = ""

    @property
    def first_added_at(self) -> str:
        """Compatibility name used by the homepage while data now calls this first_seen."""
        return self.first_seen_at

    @property
    def display_artist(self) -> str:
        return self.artist or self.album_artist or "Unknown artist"


def from_row(row) -> Track:
    return Track(
        id=row["id"], path=row["path"], title=row["title"], artist=row["display_artist"],
        album_artist=row["album_artist"], album=row["album"], genre=row["genre"],
        track_number=row["track_number"], disc_number=row["disc_number"],
        year=row["year"], duration_ms=row["duration_ms"],
        artwork_path=row["artwork_path"], artwork_accent=row["artwork_accent"],
        first_seen_at=row["first_seen_at"], size_bytes=row["size_bytes"],
        modified_ms=row["modified_ms"], missing=bool(row["missing"]),
        play_count=row["play_count"], last_played_at=row["last_played_at"],
        primary_artist=row["primary_artist"],
    )
