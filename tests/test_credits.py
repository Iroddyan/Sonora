import unittest

from sonora.credits import normalize_name, split_artist_credits


class ArtistCreditTests(unittest.TestCase):
    def test_splits_common_separators_but_preserves_default_exceptions(self):
        primary, featured = split_artist_credits("Tyler, The Creator feat. Earth, Wind & Fire & SZA")
        self.assertEqual(primary, "Tyler, The Creator")
        self.assertEqual(featured, ["Earth, Wind & Fire", "SZA"])
        self.assertEqual(split_artist_credits("AC/DC"), ("AC/DC", []))

    def test_prefers_explicit_multi_value_artist_tags(self):
        self.assertEqual(split_artist_credits(["Akon", "SZA"]), ("Akon", ["SZA"]))

    def test_normalizes_unicode_and_case_for_identity(self):
        self.assertEqual(normalize_name("  ＡＫＯＮ  "), "akon")


if __name__ == "__main__":
    unittest.main()
