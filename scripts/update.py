#!/usr/bin/env python3
"""Rebuild the list from CookLLM's public job snapshot.

Reads the two public files the CookLLM jobs board loads
(https://cookllm.com/en/jobs/board): the board, with each role's tags, and
the apply links. Keeps internships whose posting asks for a PhD, writes
data/*.json and README.md (from templates/README.md). Standard library
only, so the workflow needs no install step.

    python3 scripts/update.py            # fetch and rebuild
    python3 scripts/update.py --board board.json --links links.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from locations import places  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://cookllm.com"
SNAPSHOT = f"{SITE}/api/jobs/explorer?part="
USER_AGENT = "phd-internships-bot (+https://github.com/cookllm/AI-PhD-Internships-2027)"
UTM = "utm_source=github&utm_medium=readme&utm_campaign=phd-internships"

# The snapshot's tag lists (src/jobs/snapshot-types.ts on the site)
LEVELS = ["intern", "new_grad", "junior", "mid", "senior", "staff_plus", "manager"]
EDUCATION = ["phd_required", "phd_preferred", "masters", "bachelors", "not_mentioned"]
DIRECTIONS = ["llm", "vision", "speech", "recsys", "rl", "robotics", "driving", "science", "safety"]
FUNCTIONS = ["research", "engineering", "infra", "hardware", "data", "business", "governance", "other"]
SOURCES = ["ats", "team", "recruiter"]
PLATFORMS = ["X", "LinkedIn"]

# Sections, in README order. A role goes in the first one it fits, tried
# in PRIORITY order
SECTIONS = [
    ("llm", "LLM and NLP"),
    ("vision", "Computer Vision"),
    ("robotics", "Robotics and Autonomous Driving"),
    ("systems", "Systems and Infrastructure"),
    ("science", "AI for Science"),
    ("data", "Data Science and Recommendation"),
    ("quant", "Quantitative Research"),
    ("other", "Other ML Research"),
]
# Trading firms come first (their research is its own career path); a
# role tagged with both robotics and vision is a robotics role; an infra
# role that names LLMs is a systems role
PRIORITY = ["quant", "systems", "science", "robotics", "llm", "vision", "data", "other"]

# Trading firms, matched on the company name
QUANT_FIRMS = re.compile(
    r"point72|jane street|hudson river|jump trading|two sigma|citadel|optiver|"
    r"^imc\b|tower research|voleon|schonfeld|d\. ?e\. shaw|millennium|"
    r"susquehanna|\bsig\b|radix|xtx|g-research|five rings|\bdrw\b|de shaw",
    re.I,
)
QUANT_TITLE = re.compile(r"\bquant(itative)?\b|\btrading\b", re.I)
# For roles the model gave no research area, the title's words
TITLE_AREAS = [
    ("llm", re.compile(r"\b(llm|language|nlp|speech|agents?)\b", re.I)),
    ("vision", re.compile(r"\b(vision|image|video|graphics|3d)\b", re.I)),
    ("robotics", re.compile(r"\b(robot\w*|autonomous|driving|motor controls?)\b", re.I)),
    ("science", re.compile(r"\b(quantum|physics|biolog\w*|chemi\w*|materials?|aided engineering)\b", re.I)),
]
DATA_TITLE = re.compile(r"data scien|recommend|ranking|personaliz|\bads\b", re.I)

# How the Degree column reads. A spot check of 30 roles (2026-11-17) found
# most roles tagged phd_preferred take MS and PhD students alike, so the
# table says that rather than "preferred"
DEGREE = {"required": "PhD", "preferred": "PhD&nbsp;or&nbsp;MS"}

NEW_DAYS = 7  # roles this new get a New mark
POST_DAYS = 30  # direct posts this recent are counted
POST_ROWS = 10  # direct posts listed
MIN_ROLES = 100  # fewer than this means the snapshot is broken: stop
YEAR = re.compile(r"\b(20[2-9]\d)\b")
# A role for a year that has passed is a stale posting the careers page
# forgot to close. One for this year is kept only while it is fresh
STALE_AFTER_DAYS = 90
RESEARCHY = re.compile(r"ph\.?d|research|scientist", re.I)


def fetch(part: str) -> dict:
    req = urllib.request.Request(SNAPSHOT + part, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.load(res)


def bits(mask: int, names: list[str]) -> list[str]:
    return [name for k, name in enumerate(names) if mask >> k & 1]


def section_of(company: str, title: str, directions: list[str], function: str) -> str:
    if not directions:
        directions = [area for area, words in TITLE_AREAS if words.search(title)]
    fits = {
        "quant": bool(QUANT_FIRMS.search(company) or QUANT_TITLE.search(title)),
        "systems": function in ("infra", "hardware"),
        "science": "science" in directions,
        "robotics": "robotics" in directions or "driving" in directions,
        "llm": bool({"llm", "speech", "safety"} & set(directions)),
        "vision": "vision" in directions,
        "data": "recsys" in directions or bool(DATA_TITLE.search(title)),
        "other": True,
    }
    return next(s for s in PRIORITY if fits[s])


def stale(title: str, posted: dt.date, today: dt.date) -> bool:
    years = [int(y) for y in YEAR.findall(title)]
    if not years:
        return False
    newest = max(years)
    if newest < today.year:
        return True
    return newest == today.year and (today - posted).days > STALE_AFTER_DAYS


def tidy_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip().replace("; ", " / ")
    if title and title == title.lower():
        title = title[0].upper() + title[1:]
    return title


def site_link(place: str, path: str = "/en/jobs/board") -> str:
    """A link to CookLLM, tagged so its analytics can tell where it was"""
    return f"{SITE}{path}?{UTM}&utm_content={place}"


def build(board: dict, links: dict) -> tuple[list[dict], dict]:
    jobs = board["jobs"]
    made = dt.datetime.fromisoformat(board["generatedAt"].replace("Z", "+00:00"))
    n = len(jobs["title"])
    level = jobs.get("level") or [-1] * n
    education = jobs.get("education") or [-1] * n
    src = jobs.get("src") or [1] * n
    more = jobs.get("more") or {}
    companies = board["companies"]

    def apply_url(company: dict, stored: str) -> str:
        template = company.get("url")
        return template.replace("{id}", stored) if template and stored else stored

    def posted(i: int) -> str:
        return (made - dt.timedelta(days=jobs["age"][i])).date().isoformat()

    roles = []
    for i in range(n):
        if not src[i] & 1 or level[i] != 0 or education[i] not in (0, 1):
            continue
        company = companies[jobs["company"][i]]
        url = apply_url(company, links["url"][i])
        title = tidy_title(jobs["title"][i])
        if not url or not title:
            continue
        if stale(title, made.date() - dt.timedelta(days=jobs["age"][i]), made.date()):
            continue
        postings = [(board["locations"][jobs["location"][i]], board["countries"][jobs["country"][i]])]
        postings += [(board["locations"][loc], board["countries"][c]) for loc, c, *_ in more.get(str(i), [])]
        directions = bits(jobs["directions"][i], DIRECTIONS) if jobs.get("directions") else []
        function = FUNCTIONS[jobs["fn"][i]] if 0 <= jobs["fn"][i] < len(FUNCTIONS) else "other"
        roles.append(
            {
                "company": company["name"],
                "title": title,
                "locations": places(postings),
                "phd": "required" if education[i] == 0 else "preferred",
                "posted": posted(i),
                "section": section_of(company["name"], title, directions, function),
                "directions": directions,
                "apply": url,
            }
        )
    # Newest first; within a day, by company A to Z
    roles.sort(key=lambda r: (r["company"].lower(), r["title"]))
    roles.sort(key=lambda r: r["posted"], reverse=True)

    # Internships hiring team members posted on X or LinkedIn that are not
    # on a careers page. Who posted, the post and its link stay on CookLLM
    # for members, so only the company, title, platform and date are here
    via = jobs.get("via") or [-1] * n
    recent = []
    for i in range(n):
        if src[i] & 1 or not src[i] & 2 or level[i] != 0:
            continue
        if jobs["age"][i] > POST_DAYS:
            continue
        title = tidy_title(jobs["title"][i])
        # Posts carry no degree tag: research internships are told apart by
        # the title (the model's research function also caught thesis
        # offers, which are not internships)
        if not RESEARCHY.search(title):
            continue
        recent.append(
            {
                "company": companies[jobs["company"][i]]["name"],
                "title": title,
                "platform": PLATFORMS[via[i]] if 0 <= via[i] < len(PLATFORMS) else "",
                "posted": posted(i),
            }
        )
    recent.sort(key=lambda p: p["posted"], reverse=True)
    posts = {
        "days": POST_DAYS,
        "count": len(recent),
        "companies": len({p["company"] for p in recent}),
        "latest": recent[:POST_ROWS],
    }
    return roles, posts


# ---------- README ----------


def anchor(heading: str) -> str:
    """GitHub's heading anchor"""
    slug = re.sub(r"[^\w\- ]", "", heading.lower())
    return slug.replace(" ", "-")


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def age(posted: str, today: dt.date) -> str:
    days = max(0, (today - dt.date.fromisoformat(posted)).days)
    if days == 0:
        return "today"
    return f"{days}d" if days < 60 else f"{days // 30}mo"


def where(locations: list[str]) -> str:
    if not locations:
        return "Not listed"
    if len(locations) <= 3:
        return "<br>".join(cell(p) for p in locations)
    shown = "<br>".join(cell(p) for p in locations)
    return f"<details><summary>{len(locations)} locations</summary>{shown}</details>"


def role_table(roles: list[dict], today: dt.date) -> str:
    rows = [
        "| Company | Role | Location | Degree | Posted | Apply |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    last = None
    for r in roles:
        company = "↳" if r["company"] == last else f"**{cell(r['company'])}**"
        last = r["company"]
        new = (today - dt.date.fromisoformat(r["posted"])).days <= NEW_DAYS
        posted = age(r["posted"], today) + ("&nbsp;**New**" if new else "")
        rows.append(
            f"| {company} | {cell(r['title'])} | {where(r['locations'])} "
            f"| {DEGREE[r['phd']]} | {posted} | [Apply]({r['apply']}) |"
        )
    return "\n".join(rows)


def post_table(posts: dict, today: dt.date) -> str:
    rows = [
        "| Company | Role | Platform | Posted |",
        "| --- | --- | --- | --- |",
    ]
    # Each role links to the board on CookLLM, where members see the post
    link = site_link("direct-posts-row")
    for p in posts["latest"]:
        rows.append(
            f"| **{cell(p['company'])}** | [{cell(p['title'])}]({link}) "
            f"| {p['platform']} | {age(p['posted'], today)} |"
        )
    return "\n".join(rows)


def readme(roles: list[dict], posts: dict, tracked: int, now: dt.datetime) -> str:
    today = now.date()
    template = (ROOT / "templates" / "README.md").read_text()
    by_section = {key: [r for r in roles if r["section"] == key] for key, _ in SECTIONS}
    toc, tables = [], []
    for key, heading in SECTIONS:
        group = by_section[key]
        if not group:
            continue
        toc.append(f"  - [{heading}](#{anchor(heading)}) ({len(group)})")
        tables.append(f"### {heading}\n\n{role_table(group, today)}\n\n[Back to top](#contents)")
    values = {
        "UPDATED": now.strftime("%B %-d, %Y %H:%M"),
        "TOTAL": str(len(roles)),
        "COMPANIES": str(len({r["company"] for r in roles})),
        "TRACKED": f"{tracked:,}",
        "NEW_DAYS": str(NEW_DAYS),
        "TOC": "\n".join(toc),
        "TABLES": "\n\n".join(tables),
        "POST_DAYS": str(posts["days"]),
        "POST_COUNT": str(posts["count"]),
        "POST_TABLE": post_table(posts, today),
        "SITE_MATCH": site_link("daily-email", "/en/jobs/match"),
        "SITE_POSTS": site_link("direct-posts"),
        "SITE_HOME": site_link("footer", "/en"),
    }
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: values[m.group(1)], template)
    return out.rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--board", help="read the board from this file instead")
    parser.add_argument("--links", help="read the links from this file instead")
    parser.add_argument("--now", help="UTC time the README is written for (YYYY-MM-DDTHH:MM)")
    args = parser.parse_args()

    board = json.loads(Path(args.board).read_text()) if args.board else fetch("board")
    links = json.loads(Path(args.links).read_text()) if args.links else fetch("links")
    if board.get("generatedAt") != links.get("generatedAt"):
        print("board and links are from different snapshots, try again later", file=sys.stderr)
        return 1

    roles, posts = build(board, links)
    data = ROOT / "data"
    data.mkdir(exist_ok=True)
    last_roles = json.loads((data / "internships.json").read_text()) if (data / "internships.json").exists() else {}
    last_posts = json.loads((data / "direct-posts.json").read_text()) if (data / "direct-posts.json").exists() else {}
    before = len(last_roles.get("roles", []))
    if len(roles) < MIN_ROLES or len(roles) < before / 2:
        print(f"only {len(roles)} roles (last time {before}): not writing", file=sys.stderr)
        return 1

    now = (
        dt.datetime.fromisoformat(args.now)
        if args.now
        else dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
    )
    # "Last updated" moves only when the roles or posts change, so a rerun
    # with the same data writes the same files and nothing is committed
    same = last_roles.get("roles") == roles and {k: last_posts.get(k) for k in posts} == posts
    if same and last_roles.get("updated"):
        now = dt.datetime.fromisoformat(last_roles["updated"])
    stamp = now.isoformat()
    (data / "internships.json").write_text(
        json.dumps({"updated": stamp, "snapshot": board["generatedAt"], "roles": roles}, indent=1, ensure_ascii=False) + "\n"
    )
    (data / "direct-posts.json").write_text(
        json.dumps({"updated": stamp, "snapshot": board["generatedAt"], **posts}, indent=1, ensure_ascii=False) + "\n"
    )
    (ROOT / "README.md").write_text(readme(roles, posts, len(board["companies"]), now))
    print(f"{len(roles)} roles, {posts['count']} direct posts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
