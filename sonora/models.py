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
    first_added_at: str = ""

    @property
    def display_artist(self) -> str:
        return self.artist or self.album_artist or "Unknown artist"


def from_row(row) -> Track:
    return Track(
        id=row["id"], path=row["path"], title=row["title"], artist=row["artist"],
        album_artist=row["album_artist"], album=row["album"], genre=row["genre"],
        track_number=row["track_number"], disc_number=row["disc_number"],
        year=row["year"], duration_ms=row["duration_ms"],
        artwork_path=row["artwork_path"], artwork_accent=row["artwork_accent"],
        first_added_at=row["first_added_at"],
    )
