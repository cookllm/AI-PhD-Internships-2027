"""Turn the location strings careers pages publish into short, uniform ones.

Careers pages write the same place many ways ("US, CA, Santa Clara",
"Santa Clara, California, United States of America", "Santa Clara, CA").
The table shows "Santa Clara, CA" for US places and "City, Country"
elsewhere. Anything not recognized is kept as written.
"""

from __future__ import annotations

import re

US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "district of columbia": "DC", "florida": "FL",
    "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL",
    "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY",
    "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}
STATE_CODES = set(US_STATES.values())

US_NAMES = {
    "us", "usa", "u.s.", "u.s.a.", "united states", "united states of america",
}

# Country spellings seen on careers pages, to the name the table shows
COUNTRIES = {
    "uk": "UK", "gb": "UK", "gbr": "UK", "united kingdom": "UK",
    "england": "UK", "scotland": "UK", "great britain": "UK",
    "ca": "Canada", "can": "Canada", "canada": "Canada",
    "au": "Australia", "aus": "Australia", "australia": "Australia",
    "de": "Germany", "deu": "Germany", "germany": "Germany",
    "fr": "France", "fra": "France", "france": "France",
    "ch": "Switzerland", "che": "Switzerland", "switzerland": "Switzerland",
    "cn": "China", "chn": "China", "china": "China",
    "prc": "China",
    "in": "India", "ind": "India", "india": "India",
    "sg": "Singapore", "sgp": "Singapore", "singapore": "Singapore",
    "kr": "South Korea", "kor": "South Korea", "korea": "South Korea",
    "south korea": "South Korea", "republic of korea": "South Korea",
    "korea, republic of": "South Korea",
    "jp": "Japan", "jpn": "Japan", "japan": "Japan",
    "il": "Israel", "isr": "Israel", "israel": "Israel",
    "nl": "Netherlands", "nld": "Netherlands", "netherlands": "Netherlands",
    "es": "Spain", "esp": "Spain", "spain": "Spain",
    "it": "Italy", "ita": "Italy", "italy": "Italy",
    "se": "Sweden", "swe": "Sweden", "sweden": "Sweden",
    "pl": "Poland", "pol": "Poland", "poland": "Poland",
    "tw": "Taiwan", "twn": "Taiwan", "taiwan": "Taiwan",
    "hk": "Hong Kong", "hong kong": "Hong Kong",
    "ie": "Ireland", "irl": "Ireland", "ireland": "Ireland",
    "dk": "Denmark", "dnk": "Denmark", "denmark": "Denmark",
    "fi": "Finland", "fin": "Finland", "finland": "Finland",
    "at": "Austria", "aut": "Austria", "austria": "Austria",
    "be": "Belgium", "bel": "Belgium", "belgium": "Belgium",
    "br": "Brazil", "bra": "Brazil", "brazil": "Brazil",
    "mx": "Mexico", "mex": "Mexico", "mexico": "Mexico",
    "ae": "UAE", "are": "UAE", "united arab emirates": "UAE",
    "ro": "Romania", "rou": "Romania", "romania": "Romania",
    "lu": "Luxembourg", "lux": "Luxembourg", "luxembourg": "Luxembourg",
    "vn": "Vietnam", "vnm": "Vietnam", "vietnam": "Vietnam",
    "pt": "Portugal", "prt": "Portugal", "portugal": "Portugal",
    "cz": "Czechia", "cze": "Czechia", "czechia": "Czechia",
    "czech republic": "Czechia", "nz": "New Zealand",
    "new zealand": "New Zealand", "no": "Norway", "nor": "Norway",
    "norway": "Norway", "gr": "Greece", "grc": "Greece", "greece": "Greece",
}

# Canadian provinces, read as Canada when the snapshot says the role is
# there ("Toronto, ON")
PROVINCES = {"ON", "QC", "BC", "AB", "MB", "NS", "NB", "SK", "NL", "PE"}

CITY_NICKNAMES = {"sf": "San Francisco", "nyc": "New York City"}

# Countries a bare two-letter code is read as (only these: "CA" and "IN"
# are also US states, so a lone code is a state unless the string says
# otherwise)
ISO2 = {
    "GB": "UK", "CA": "Canada", "AU": "Australia", "DE": "Germany",
    "FR": "France", "CH": "Switzerland", "CN": "China", "IN": "India",
    "SG": "Singapore", "KR": "South Korea", "JP": "Japan", "IL": "Israel",
    "NL": "Netherlands", "ES": "Spain", "IT": "Italy", "SE": "Sweden",
    "PL": "Poland", "TW": "Taiwan", "HK": "Hong Kong", "IE": "Ireland",
    "DK": "Denmark", "FI": "Finland", "AT": "Austria", "BE": "Belgium",
    "BR": "Brazil", "MX": "Mexico", "AE": "UAE",
}

REMOTE = re.compile(r"\b(remote|virtual)\b", re.I)
WORK_MODE = re.compile(r"\((hybrid|remote|on-?site)\)", re.I)
MULTIPLE = re.compile(r"^(\d+ locations|multiple locations|blank)$", re.I)
# Workday site codes: "US-CA-Fremont (1003)", "SG-Singapore (3301)"
SITE_CODE = re.compile(r"^([A-Z]{2,3})-(?:([A-Z]{2})-)?([^()]+?)(?:\s*\(\d+\))?$")
# A street address with the city in brackets: "607 Hansen (Palo Alto California)"
ADDRESS = re.compile(r"^\d+.*\(([^()]+)\)$")


def _clean(part: str) -> str:
    return re.sub(r"\s+", " ", part).strip(" ,.-:")


def _state(token: str) -> str | None:
    t = token.strip().rstrip(".")
    if len(t) == 2 and t.upper() in STATE_CODES:
        return t.upper()
    return US_STATES.get(t.lower())


def _country(token: str) -> str | None:
    return COUNTRIES.get(token.strip().rstrip(".").lower())


def _country_of(code: str) -> str:
    if code == "US":
        return "United States"
    return ISO2.get(code, "")


def _city_state(text: str) -> str | None:
    """'Palo Alto California' or 'Champaign Illinois' -> 'Palo Alto, CA'"""
    words = text.split()
    for k in (2, 1):
        if len(words) > k and _state(" ".join(words[-k:])):
            return f"{' '.join(words[:-k])}, {_state(' '.join(words[-k:]))}"
    return None


def one(place: str, country: str = "") -> list[str]:
    """
    One location entry, in the table's form: usually one place, several
    when the entry lists cities ("New York, Seattle"). `country` is the
    snapshot's ISO code for the role
    """
    text = _clean(place)
    if not text or MULTIPLE.match(text.replace("BLANK,", "").strip(" ,")):
        if country == "REMOTE":
            return ["Remote"]
        rest = [p for p in (_clean(x) for x in text.split(",")) if p]
        named = [_country(p) for p in rest if _country(p)]
        if named:
            return [named[0]]
        if _country_of(country):
            return [_country_of(country)]
        return ["Multiple locations"] if text else []

    address = ADDRESS.match(text)
    if address and _city_state(address.group(1)):
        return [_city_state(address.group(1))]

    # "Seattle-WA-2nd Ave", "IND19-01-Bengaluru-EPIP 122"
    dashed = re.match(r"^([A-Z][a-z][A-Za-z .]*)-([A-Z]{2})-", text)
    if dashed and _state(dashed.group(2)):
        return [f"{dashed.group(1)}, {dashed.group(2)}"]
    dashed = re.match(r"^([A-Z]{3})\d+-\d+-([A-Za-z ]+)-", text)
    if dashed and _country(dashed.group(1)):
        return [f"{dashed.group(2)}, {_country(dashed.group(1))}"]

    if REMOTE.search(text) and len(text) <= 24:
        rest = _clean(REMOTE.sub("", text).strip("()-,/ "))
        if not rest:
            return ["Remote"]
        if rest.lower() in US_NAMES:
            return ["Remote (US)"]
        return [f"Remote ({_country(rest) or rest})"]

    mode = WORK_MODE.search(text)
    text = _clean(re.sub(r"\([^()]*\)", "", text))
    text = re.sub(r"\s+Office$", "", text, flags=re.I)


    code = SITE_CODE.match(text)
    if code and (_country(code.group(1)) or code.group(1) in ISO2 or code.group(1) == "US"):
        city = _clean(code.group(3))
        if code.group(1) == "US" and code.group(2):
            return [f"{city}, {code.group(2)}"]
        if not re.search(r"\d", city):
            return one(city, country)

    # "UK - London", "US - Austin, TX", "Hybrid - San Francisco, CA",
    # "California - Palo Alto"
    if " - " in text:
        head, tail = (_clean(x) for x in text.split(" - ", 1))
        if head.lower() in US_NAMES or _country(head) or head.lower() in ("hybrid", "onsite", "on-site"):
            return one(tail, country if head.lower() not in ("uk",) else "GB")
        if _state(head):
            return [f"{tail}, {_state(head)}"]

    text = CITY_NICKNAMES.get(text.lower(), text)
    # "Cambridge, MA USA" -> "Cambridge, MA, USA"
    text = re.sub(r"\b([A-Z]{2}) (USA|US)$", r"\1, \2", text)
    parts = [p for p in (_clean(p) for p in text.split(",")) if p]
    if not parts:
        return []
    out = _parts(parts, country)
    if mode and mode.group(1).lower() == "hybrid":
        out = [f"{p} (hybrid)" for p in out]
    return out


def _parts(parts: list[str], country: str) -> list[str]:
    parts = [p for p in parts if not MULTIPLE.match(p)] or parts
    # "Korea, Republic of": join the pieces of country names
    joined = ", ".join(parts[-2:]).lower()
    if len(parts) >= 2 and joined in COUNTRIES:
        parts = parts[:-2] + [COUNTRIES[joined]]
    low = [p.lower() for p in parts]

    if len(parts) == 1:
        p = parts[0]
        if low[0] in US_NAMES:
            return ["United States"]
        if _country(p):
            return [_country(p)]
        abroad = _country_of(country)
        if country not in ("US", "", "REMOTE") and abroad and abroad != p:
            return [f"{p}, {abroad}"]
        return [p]

    # Country first: "US, CA, Santa Clara", "United States, Washington, Redmond"
    if len(parts) >= 3 and low[0] in US_NAMES and _state(parts[1]):
        return [f"{parts[-1]}, {_state(parts[1])}"]
    if _country(parts[0]) and not _country(parts[-1]) and not _state(parts[-1]):
        if not (len(parts) == 2 and _state(parts[0])):
            return [f"{parts[-1]}, {_country(parts[0])}"]

    # Drop a trailing US name: "Seattle, Washington, USA" -> "Seattle, WA"
    if low[-1] in US_NAMES:
        parts = parts[:-1]
        if len(parts) >= 2 and _state(parts[-1]):
            return [f"{parts[0]}, {_state(parts[-1])}"]
        return [", ".join(parts)]

    # "Toronto, ON" in Canada
    if len(parts) == 2 and country == "CA" and parts[1].upper() in PROVINCES:
        return [f"{parts[0]}, Canada"]
    # "Mountain View, CA" / "Mountain View, California"
    if len(parts) == 2 and _state(parts[1]) and country in ("US", ""):
        return [f"{parts[0]}, {_state(parts[1])}"]

    # "City, Region, Country" or "City, Country" outside the US
    last = _country(parts[-1]) or ISO2.get(parts[-1].upper())
    if last:
        return [last] if parts[0] == last else [f"{parts[0]}, {last}"]

    # "New York, Seattle": a list of cities
    if not any(_state(p) for p in parts[1:]):
        return parts
    return [", ".join(parts)]


def split(location: str) -> list[str]:
    """A careers page's location field: one place, or several"""
    return [
        p
        for p in re.split(r"\s*[;|•]\s*|\s+/\s+|\s+or\s+|:\s+(?=[A-Z])", location)
        if p.strip()
    ]


def places(postings: list[tuple[str, str]]) -> list[str]:
    """Every place of a role's postings, short and without repeats"""
    out: list[str] = []
    for location, country in postings:
        for part in split(location) or [""]:
            for p in one(part, country):
                if p and p not in out:
                    out.append(p)
    # "San Jose" next to "San Jose, CA" says nothing more
    return [p for p in out if not any(q.startswith(p + ", ") for q in out)]
