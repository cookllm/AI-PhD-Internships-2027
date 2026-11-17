import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import update  # noqa: E402


def snapshot():
    # Three careers-page roles and two posts, in the snapshot's columns
    titles = ["Research Intern, LLMs", "Research Intern, Vision", "Software Engineer", "PhD Research Intern", "Marketing Intern"]
    return {
        "generatedAt": "2026-11-17T08:00:00.000Z",
        "companies": [{"name": "Acme", "url": "https://jobs.example/{id}"}, {"name": "Point72"}],
        "countries": ["US", "GB"],
        "locations": ["Seattle, WA", "London"],
        "jobs": {
            "title": titles,
            "company": [0, 1, 0, 0, 0],
            "country": [0, 1, 0, 0, 0],
            "location": [0, 1, 0, 0, 0],
            "fn": [0, 0, 1, 0, 5],
            "age": [2, 20, 1, 3, 3],
            "posts": [1, 1, 1, 1, 1],
            "level": [0, 0, 3, 0, 0],
            "education": [0, 1, 0, -1, -1],
            "directions": [1, 2, 0, 0, 0],
            "src": [1, 1, 1, 2, 2],
            "via": [-1, -1, -1, 0, 1],
            "post": ["", "", "", "abc", "def"],
        },
    }


LINKS = {"generatedAt": "2026-11-17T08:00:00.000Z", "url": ["11", "https://p72.example/22", "33", "", ""], "more": {}}


class Build(unittest.TestCase):
    def test_keeps_phd_internships_only(self):
        roles, _ = update.build(snapshot(), LINKS)
        self.assertEqual([r["title"] for r in roles], ["Research Intern, LLMs", "Research Intern, Vision"])
        self.assertEqual(roles[0]["apply"], "https://jobs.example/11")
        self.assertEqual(roles[0]["section"], "llm")
        # A trading firm's role goes under quantitative research
        self.assertEqual(roles[1]["section"], "quant")
        self.assertEqual(roles[1]["phd"], "preferred")

    def test_posts_keep_no_author_text_or_link(self):
        _, posts = update.build(snapshot(), LINKS)
        self.assertEqual(posts["count"], 1)
        self.assertEqual(set(posts["latest"][0]), {"company", "title", "platform", "posted"})
        self.assertEqual(posts["latest"][0]["platform"], "X")

    def test_past_years_are_stale(self):
        today = update.dt.date(2026, 11, 17)
        self.assertTrue(update.stale("2025 Summer Intern", today, today))
        self.assertTrue(update.stale("Intern, Fall 2026", update.dt.date(2026, 4, 24), today))
        self.assertFalse(update.stale("Intern, Fall 2026", update.dt.date(2026, 10, 12), today))
        self.assertFalse(update.stale("2026-2027 PhD Intern", update.dt.date(2025, 1, 1), today))
        self.assertFalse(update.stale("Research Intern", update.dt.date(2024, 8, 16), today))

    def test_site_links_are_tagged(self):
        self.assertIn("utm_source=github&utm_medium=phd-internships", update.site_link("x"))

    def test_anchor_matches_github(self):
        self.assertEqual(update.anchor("Robotics and Autonomous Driving"), "robotics-and-autonomous-driving")
        self.assertEqual(update.anchor("Posted by hiring teams, not on careers pages"), "posted-by-hiring-teams-not-on-careers-pages")


if __name__ == "__main__":
    unittest.main()
