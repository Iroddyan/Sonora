import unittest
import time

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

    def test_listening_progress_counts_forward_playback_but_not_seeks_or_pauses(self):
        class PositionPlaybackService(PlaybackService):
            position_ms = 0

            @property
            def position_us(self):
                return self.position_ms * 1000

        saved = []
        service = PositionPlaybackService(on_listened=lambda _session, amount: saved.append(amount))
        try:
            service._session_id = 7
            service._session_track = track(1)
            service.playing = True
            service._last_position_ms = 0
            service._last_sample_time = time.monotonic() - 1
            service._last_checkpoint = time.monotonic()
            service.position_ms = 1_000
            service.record_progress()
            self.assertEqual(service._pending_listened_ms, 1_000)

            service._last_sample_time = time.monotonic() - 1
            service._last_position_ms = 1_000
            service.position_ms = 30_000  # A seek-sized jump is not listening time.
            service.record_progress()
            self.assertEqual(service._pending_listened_ms, 1_000)

            service.playing = False
            service._last_position_ms = 30_000
            service._last_sample_time = time.monotonic() - 1
            service.position_ms = 31_000
            service.record_progress()
            self.assertEqual(service._pending_listened_ms, 1_000)
            service._finish_session("stopped")
            self.assertEqual(saved, [1_000])
        finally:
            service._session_id = None
            service._session_track = None
            service.close()


if __name__ == "__main__":
    unittest.main()
