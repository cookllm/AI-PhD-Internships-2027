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

    def test_company_once_title_is_the_link(self):
        today = update.dt.date(2026, 11, 17)
        roles = [
            {"company": "Acme", "title": "Research Intern, LLMs", "locations": ["Seattle, WA"], "phd": "required", "posted": "2026-11-15", "apply": "https://a.example/1"},
            {"company": "Acme", "title": "Research Intern, Vision", "locations": ["A", "B", "C"], "phd": "preferred", "posted": "2026-11-10", "apply": "https://a.example/2"},
            {"company": "Solo", "title": "PhD Intern", "locations": [], "phd": "required", "posted": "2026-11-16", "apply": "https://s.example/1"},
        ]
        out = update.company_blocks(roles, today, update.role_line(today))
        self.assertEqual(out.count("#### Acme"), 1)
        self.assertIn("#### Acme <sub>2 roles</sub>", out)
        self.assertIn("#### Solo\n", out)
        self.assertTrue(out.index("#### Solo") < out.index("#### Acme"))
        self.assertIn("- [Research Intern, LLMs](https://a.example/1)", out)
        self.assertIn("A; B +1&emsp;PhD or MS&emsp;7d", out)
        self.assertNotIn("Apply", out)
        self.assertNotIn("↳", out)

    def test_site_links_are_tagged(self):
        self.assertIn("utm_source=github&utm_medium=readme&utm_campaign=phd-internships&utm_content=x", update.site_link("x"))

    def test_anchor_matches_github(self):
        self.assertEqual(update.anchor("Robotics and Autonomous Driving"), "robotics-and-autonomous-driving")
        self.assertEqual(update.anchor("Internships posted by research teams"), "internships-posted-by-research-teams")


if __name__ == "__main__":
    unittest.main()
