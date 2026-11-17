import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from locations import places  # noqa: E402

CASES = [
    (("US, CA, Santa Clara", "US"), ["Santa Clara, CA"]),
    (("United States, Washington, Redmond", "US"), ["Redmond, WA"]),
    (("Santa Clara, California, United States of America", "US"), ["Santa Clara, CA"]),
    (("Cambridge, MA USA; San Francisco, CA USA", "US"), ["Cambridge, MA", "San Francisco, CA"]),
    (("London, England, United Kingdom", "GB"), ["London, UK"]),
    (("London", "GB"), ["London, UK"]),
    (("Seoul, Korea, Republic of", "KR"), ["Seoul, South Korea"]),
    (("Toronto, ON", "CA"), ["Toronto, Canada"]),
    (("US-CA-Fremont (1003)", "US"), ["Fremont, CA"]),
    (("607 Hansen (Palo Alto California)", "US"), ["Palo Alto, CA"]),
    (("UK - London", "GB"), ["London, UK"]),
    (("Pittsburgh, PA or Remote (US)", "US"), ["Pittsburgh, PA", "Remote (US)"]),
    (("New York, Seattle", "US"), ["New York", "Seattle"]),
    (("Washington, DC", "US"), ["Washington, DC"]),
    (("2 Locations", ""), ["Multiple locations"]),
    (("Remote", "REMOTE"), ["Remote"]),
    (("Hong Kong, Hong Kong", "HK"), ["Hong Kong"]),
]


class Places(unittest.TestCase):
    def test_cases(self):
        for (raw, country), want in CASES:
            with self.subTest(raw=raw):
                self.assertEqual(places([(raw, country)]), want)

    def test_postings_merge_without_repeats(self):
        got = places([("Seattle, WA", "US"), ("Seattle, Washington, USA", "US"), ("London", "GB")])
        self.assertEqual(got, ["Seattle, WA", "London, UK"])
        # A bare city next to the same city with its state is one place
        self.assertEqual(places([("San Jose", "US"), ("San Jose, CA", "US")]), ["San Jose, CA"])


if __name__ == "__main__":
    unittest.main()
