import unittest
import os

import gi
gi.require_version("Gio", "2.0")
from sonora.mpris import MprisService


class FakePlayback:
    current_track = None
    playing = False
    stopped = True
    loop_status = "None"
    shuffle_enabled = False
    queue = []
    index = -1
    position_us = 0
    duration_us = 0
    volume = 0.8

    def set_volume(self, value):
        self.volume = value

    def set_loop_status(self, value):
        self.loop_status = value

    def set_shuffle(self, value):
        self.shuffle_enabled = value

    def next(self): pass
    def previous(self): pass
    def toggle(self): pass
    def stop(self): pass
    def seek(self, _value): pass


class MprisTests(unittest.TestCase):
    def test_exports_player_on_session_bus_when_available(self):
        if not os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
            self.skipTest("No session bus is available")
        service = MprisService(FakePlayback(), lambda: None, lambda: None, lambda _uri: False)
        try:
            self.assertTrue(service.connection)
            self.assertTrue(service._registrations)
            self.assertIn(service._owner_result, (1, 4))
        finally:
            service.close()
if __name__ == "__main__":
    unittest.main()
