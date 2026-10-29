import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analyzer"))
import parse

EVENTS = [
    {"eventid": "cowrie.session.connect", "timestamp": "2026-10-16T10:00:00Z", "src_ip": "203.0.113.5"},
    {"eventid": "cowrie.login.failed", "username": "root", "password": "123456"},
    {"eventid": "cowrie.login.success", "username": "root", "password": "admin"},
    {"eventid": "cowrie.command.input", "input": "uname -a  "},
    {"eventid": "cowrie.session.connect", "timestamp": "2026-10-17T11:00:00Z", "src_ip": "2001:db8:1:2::1"},
]
GEO = {"203.0.113.5": {"country": "Testland", "lat": 1.0, "lon": 2.0}}


class ParseTest(unittest.TestCase):
    def test_totals_and_tops(self):
        s = parse.summarize(EVENTS, GEO)
        self.assertEqual(s["totals"], {"sessions": 2, "unique_ips": 2, "login_attempts": 2, "login_successes": 1})
        self.assertEqual(s["top_usernames"], [{"label": "root", "count": 2}])
        self.assertEqual(s["top_commands"], [{"label": "uname -a", "count": 1}])
        self.assertEqual([d["day"] for d in s["timeline"]], ["2026-10-16", "2026-10-17"])

    def test_only_geolocated_ips_on_map_and_masked(self):
        s = parse.summarize(EVENTS, GEO)
        self.assertEqual(len(s["points"]), 1)
        self.assertEqual(s["points"][0]["ip"], "203.0.113.x")
        self.assertEqual(s["top_countries"], [{"label": "Testland", "count": 1}])

    def test_mask_ipv6(self):
        self.assertEqual(parse.mask_ip("2001:db8:1:2::1"), "2001:db8:1:x")

    def test_read_events_skips_truncated_line(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "cowrie.json"
            f.write_text(json.dumps(EVENTS[0]) + '\n{"eventid": "cowrie.sess')
            self.assertEqual(len(list(parse.read_events([f]))), 1)

    def test_offline_geolocation_uses_cache_only(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "geo.json"
            cache.write_text(json.dumps(GEO))
            self.assertEqual(parse.geolocate({"203.0.113.5", "198.51.100.9"}, cache, offline=True), GEO)


if __name__ == "__main__":
    unittest.main()
