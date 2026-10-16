import unittest

from sonora.hygiene import clean_title_metadata


class HygieneSuggestionTests(unittest.TestCase):
    def test_splits_artist_title_and_removes_bracketed_video_noise(self):
        self.assertEqual(clean_title_metadata("Artist Name - Song Name (Official Video)"),
                         {"title": "Song Name", "artist": "Artist Name"})

    def test_only_splits_artist_prefix_when_it_matches_existing_artist(self):
        self.assertEqual(clean_title_metadata("Artist Name - Song Name [Lyrics]", "Artist Name"),
                         {"title": "Song Name"})
        self.assertEqual(clean_title_metadata("A - B - C", "Different Artist"), {})

    def test_preserves_parenthetical_text_that_is_not_known_video_noise(self):
        self.assertEqual(clean_title_metadata("Song (Live at Wembley)"), {})

    def test_recognizes_accented_video_labels(self):
        self.assertEqual(clean_title_metadata("Artist - Song (Official Vidéo)"),
                         {"title": "Song", "artist": "Artist"})


if __name__ == "__main__":
    unittest.main()
