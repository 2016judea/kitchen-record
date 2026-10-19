#!/usr/bin/env python3
"""Read each candidate restaurant's OWN website (homepage + common contact paths) and keep the
email only if it is printed there today. Writes outreach/round1/verified.csv (gitignored) with
email_source = the page URL it was read on and email_source_date = today. Sends nothing.
Overture's listing email is a lead, not a source: on 2026-10-19 it matched a DoubleTree to
starbucks.com, so nothing goes to the drafter that its own site doesn't print."""
import csv, re, sys, datetime, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "outreach" / "round1" / "candidates.csv"
OUT = ROOT / "outreach" / "round1" / "verified.csv"
TODAY = datetime.date.today().isoformat()
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
BAD = re.compile(r"\.(png|jpg|jpeg|gif|svg|webp|js|css)$|@2x|example\.|sentry|wixpress|godaddy|squarespace|domain\.com|email\.com|noreply|no-reply|yourname|user@|name@", re.I)
PATHS = ["", "contact", "contact-us", "about", "about-us", "info", "catering", "events"]


def get(url):
    try:
        out = subprocess.run(["curl", "-sL", "--max-time", "12", "-A", "Mozilla/5.0 (Macintosh) Safari/605", url],
                             capture_output=True, timeout=20).stdout
        return out.decode("utf8", "ignore")
    except Exception:
        return ""


def site_of(src):
    m = re.search(r"\((https?://[^)\s]+)\)", src)
    return m.group(1) if m else ""


def check(c):
    site = site_of(c["email_source"])
    if not site:
        return None
    base = re.match(r"https?://[^/]+", site).group(0)
    want = c["email"].lower()
    found = {}
    for p in PATHS:
        url = site if p == "" else f"{base}/{p}"
        html = get(url).replace("&#64;", "@").replace("%40", "@")
        for e in EMAIL.findall(html):
            e = e.lower().rstrip(".")
            if not BAD.search(e):
                found.setdefault(e, url)
        if want in found:
            break
    if want in found:
        return {**c, "website": site, "email_source": found[want], "email_source_date": TODAY}
    # their own site prints a different address on its own domain: use that one
    host = re.sub(r"^www\.", "", re.match(r"https?://([^/]+)", site).group(1).lower())
    own = [e for e in found if e.split("@")[1].endswith(host)]
    if own:
        return {**c, "email": own[0], "website": site, "email_source": found[own[0]], "email_source_date": TODAY}
    return None


def main():
    rows = list(csv.DictReader(IN.open()))
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else len(rows)
    rows = rows[:lim]
    with ThreadPoolExecutor(12) as ex:
        res = [r for r in ex.map(check, rows) if r]
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(res[0].keys()))
        w.writeheader(); w.writerows(res)
    print(f"{len(res)} of {len(rows)} candidates print the email on their own site -> {OUT}")


if __name__ == "__main__":
    main()
