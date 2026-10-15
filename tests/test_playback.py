import unittest

from sonora.models import Track
from sonora.playback import PlaybackService


def track(identifier):
    return Track(identifier, f"/music/{identifier}.mp3", str(identifier), "Artist", "Artist", "Album",
                 "", identifier, 1, 2026, 1000, "", "")


class PlaybackServiceTests(unittest.TestCase):
    def test_shuffle_keeps_current_track_and_restores_order(self):
        service = PlaybackService()
        try:
            service._natural_queue = [track(1), track(2), track(3), track(4)]
            service.queue = list(service._natural_queue)
            service.index = 2
            current = service.current_track
            service.set_shuffle(True)
            self.assertEqual(service.current_track.path, current.path)
            self.assertEqual(service.index, 0)
            service.set_shuffle(False)
            self.assertEqual([item.path for item in service.queue], [f"/music/{i}.mp3" for i in range(1, 5)])
            self.assertEqual(service.current_track.path, current.path)
            self.assertEqual(service.index, 2)
        finally:
            service.close()

    def test_loop_status_accepts_only_mpris_values(self):
        service = PlaybackService()
        try:
            service.set_loop_status("Playlist")
            self.assertEqual(service.loop_status, "Playlist")
            service.set_loop_status("Bogus")
            self.assertEqual(service.loop_status, "Playlist")
        finally:
            service.close()


if __name__ == "__main__":
    unittest.main()
