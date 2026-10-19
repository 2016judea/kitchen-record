#!/usr/bin/env python3
"""Round-1 drafts, three segments, A/B alternated within each segment. SENDS NOTHING.

Inputs (all gitignored, local):
  outreach/round1/verified_named.csv  restaurants whose OWN site printed the email today (verify_sites.py)
  GROUPS / TRAINERS below             read off their own sites 2026-10-19 (kr_emails.sh / page title)
Writes outreach/round1/ledger.csv and outreach/round1/drafts/<token>.txt, then run scripts/build_for.py.
Dedupe against ~/Desktop/outreach-ledger/outreach.duckdb `contacted`, by email AND by domain.
A/B (one variable, pooled across the seven shelf products): A names the price in the email, B leaves it to the page.
"""
import csv, datetime, hashlib, json, re
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
R1 = ROOT / "outreach" / "round1"
SITE = "https://kitchen-record.vercel.app"
SUBSTACK = "https://randomaidan.substack.com/p/business-prototypes"
TODAY = datetime.date.today().isoformat()
F = json.loads((ROOT / "site" / "public" / "data" / "free.json").read_text())
BY = {r["id"]: r for r in F["rows"]}
M, NB = F["meta"], F["nb"]
PRICE = M["price_usd"]
FREEMAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com", "msn.com", "comcast.net"}

# Not the restaurant's own inbox (chain or wrong business), or the org is reached through its group below.
SKIP_IDS = {"LIC369761", "LIC421899", "LIC423439", "LIC368688", "LIC35627", "LIC35610", "LIC344366", "LIC30494",
            "LIC50988", "LIC29881", "LIC36411", "LIC394546", "LIC360908", "LIC370030", "LIC413219"}

GROUPS = [  # (group, email, name, source url, facility ids in Minneapolis)
    ("Kim Bartmann's restaurants", "askus@barbette.com", "", "https://www.barbette.com/", ["LIC32049", "LIC373185", "LIC50988"]),
    ("Blue Plate Restaurant Co.", "longfellowgrill@blueplateco.com", "", "https://www.longfellowgrill.com/", ["LIC29881", "LIC40822"]),
    ("Jester Concepts", "info@jesterconcepts.com", "", "https://www.jesterconcepts.com/", ["LIC402718", "LIC43485"]),
    ("Entourage Events Group", "info@thentourage.com", "", "https://entourageeventsgroup.com/", ["LIC48813", "LIC370901"]),
    ("Hai Hai, Hola Arepa and Gray Fox", "info@holaarepa.com", "", "https://holaarepa.com/", ["LIC36411", "LIC412276", "LIC354528", "LIC365994", "LIC403871", "LIC394546"]),
    ("Martina, Colita, Porzana and Rosalia", "dine@martinarestaurant.com", "", "https://www.martinarestaurant.com/", ["LIC360908", "LIC370030", "LIC407140", "LIC417809"]),
]
TRAINERS = [  # (org, email, name, source url, their own words)
    ("Safe Food Training", "info@safefoodtraining.com", "", "https://www.safefoodtraining.com/contact-us/",
     "Your site sells the Food Manager Certification MN (CFPM) course, and says every Minnesota restaurant needs one full-time certified food manager."),
    ("Food Safety Guy", "info@foodsafetyguy.com", "", "https://foodsafetyguy.com/",
     "Your site says you specialize in food safety training, ServSafe certification and MN CFPM recertification, with in-person classes in Minnesota."),
    ("Johnson Food Service Consulting", "brian.johnson@johnsonfoodserviceconsulting.com", "Brian", "https://www.johnsonfoodserviceconsulting.com/",
     "Your site says you help restaurants with training and compliance across Minnesota, Wisconsin and the Midwest."),
    ("Hospitality Minnesota", "info@hospitalitymn.com", "", "https://www.hospitalityminnesota.com/",
     "Your Training & Education page runs the National Restaurant Association programs for Minnesota operators through HMEF."),
    ("Food Safety MN", "foodsafetymn@gmail.com", "", "https://foodsafetymn.com/contact",
     "Your homepage schedules people for CFPM and ServSafe Food Protection Manager certifications."),
    ("CKC Good Food", "dave.kayoum@ckcgoodfood.com", "Dave", "https://www.ckcgoodfood.com/",
     "Your site says CKC Good Food is a food service partner for public and private contracted meal programs."),
]


def fmtd(d):
    y, m, dd = map(int, d.split("-"))
    return datetime.date(y, m, dd).strftime("%b %-d, %Y")


def nice(s):
    s = re.sub(r"\s+", " ", s).strip().title().replace("'S ", "'s ").replace("'S", "'s")
    return re.sub(r"\b(Llc|Ne|Se|Nw|Sw)\b", lambda m: m.group(1).upper(), s)


def tok(email):
    return hashlib.sha1(f"kitchen-record/{email}".encode()).hexdigest()[:10]


def record_lines(r, own=True):
    last = r["last"]
    you = "your" if own else "its"
    l1 = f"The city's last routine inspection at {nice(r['address'])} was {fmtd(last['d'])}: {'an' if str(last['s']).startswith(('8','18')) or last['s'] in (11,) else 'a'} {last['s']}."
    if r.get("top"):
        t = r["top"]
        l1 += f" \"{t['short']}\" is on {t['times']} of {you} inspections since 2023, last on {fmtd(t['last'])}."
    nb = NB.get(r["nb"] or "")
    if nb:
        l2 = f"The middle {r['nb']} restaurant scores {nb['p50']:g}, and the bottom tenth {nb['p10']:g} or lower."
    else:
        l2 = f"The middle Minneapolis restaurant scores {M['city']['p50']:g}, and the bottom tenth {M['city']['p10']:g} or lower."
    l2 += f" The city comes back about two weeks after any score of {M['rule_score']} or lower ({round(M['fu_rate_le']*100)} in 100 times, measured)."
    return l1, l2


def body(greet, l1, l2, link, variant, offer_thing):
    lines = [f"{greet},", "", l1, "", l2, ""]
    poke = f"Your scores and the line the inspector keeps writing are open to poke at, no login: {link}"
    if variant == "A":
        poke += f" The full {offer_thing} is ${PRICE}, once."
    lines += [poke, "", f"How this gets built: {SUBSTACK}", "", "Aidan", "Brick & Mortar", ""]
    return "\n".join(lines)


def main():
    led = duckdb.connect(str(Path.home() / "Desktop/outreach-ledger/outreach.duckdb"), read_only=True)
    seen = {r[0].lower() for r in led.execute("select recipient_key from contacted").fetchall() if r[0]}
    seen_dom = {e.split("@")[1] for e in seen if "@" in e} - FREEMAIL
    rows, used = [], set()

    def ok(email):
        e = email.lower(); d = e.split("@")[1]
        if e in seen or e in used or (d not in FREEMAIL and (d in seen_dom or d in {u.split("@")[1] for u in used})):
            return False
        used.add(e); return True

    fix_thing = "fix list (what the inspector checks on each repeated line and what to do), follow-up risk and named neighbour table"
    n = {"restaurant": 0, "group": 0, "trainer": 0}
    for c in csv.DictReader((R1 / "verified_named.csv").open()):
        if c["facility_id"] in SKIP_IDS or c["facility_id"] not in BY or not ok(c["email"]):
            continue
        if n["restaurant"] >= 39:
            break
        r = BY[c["facility_id"]]
        v = "AB"[n["restaurant"] % 2]; n["restaurant"] += 1
        l1, l2 = record_lines(r)
        rows.append(dict(token=tok(c["email"]), variant=v, segment="restaurant", company=nice(r["name"]), name="", email=c["email"].lower(),
                         email_source=c["email_source"], email_source_date=c["email_source_date"], own_record=l1, facility_id=r["id"],
                         status="draft", hold_reason="", subject_company=nice(r["name"]), l1=l1, l2=l2, thing=fix_thing))
    for g, email, name, src, ids in GROUPS:
        if not ok(email):
            continue
        locs = [BY[i] for i in ids if i in BY]
        worst = max(locs, key=lambda r: ((r.get("top") or {}).get("times", 0), -r["last"]["s"]))
        v = "AB"[n["group"] % 2]; n["group"] += 1
        l1, l2 = record_lines(worst)
        l1 = f"{nice(worst['name'])}: " + l1
        l2 = f"The city inspects {len(locs)} of your Minneapolis kitchens; " + l2[0].lower() + l2[1:]
        rows.append(dict(token=tok(email), variant=v, segment="group", company=g, name=name, email=email, email_source=src,
                         email_source_date=TODAY, own_record=l1, facility_id=worst["id"], status="draft", hold_reason="",
                         subject_company=g, l1=l1, l2=l2, thing=fix_thing + ", for every one of your kitchens on one password"))
    ex = BY[M["example"]]
    for org, email, name, src, words in TRAINERS:
        if not ok(email):
            continue
        v = "AB"[n["trainer"] % 2]; n["trainer"] += 1
        l2 = (f"The city's file adds this: {M['n_repeat']} of {M['n_restaurants']:,} Minneapolis restaurants have the same Priority-1 line on two or more "
              f"inspections since 2023. The full record names each one and the fix for every repeated line.")
        rows.append(dict(token=tok(email), variant=v, segment="trainer", company=org, name=name, email=email, email_source=src,
                         email_source_date=TODAY, own_record=words, facility_id=ex["id"], status="draft",
                         hold_reason="", subject_company=org, l1=words, l2=l2,
                         thing="record (fix list, follow-up risk, named neighbours) is one password for every Minneapolis restaurant, so"))
    (R1 / "drafts").mkdir(exist_ok=True)
    for f in (R1 / "drafts").glob("*.txt"):
        f.unlink()
    out = []
    for r in rows:
        link = f"{SITE}/for/{r['token']}/"
        greet = f"Hi {r['name']}" if r["name"] else "Hello"
        if r["segment"] == "trainer":
            poke = (f"Every Minneapolis restaurant's scores, and the line the inspector keeps writing them up for, are open to poke at, no login: {link}"
                    + (f" The full record for every restaurant is ${PRICE}, once, on one password." if r["variant"] == "A" else ""))
            txt = "\n".join([f"{greet},", "", r["l1"], "", r["l2"], "", poke, "", f"How this gets built: {SUBSTACK}", "", "Aidan", "Brick & Mortar", ""])
        else:
            txt = body(greet, r["l1"], r["l2"], link, r["variant"], r["thing"])
        (R1 / "drafts" / f"{r['token']}.txt").write_text(f"To: {r['email']}\nSubject: bricks / {r['subject_company']}\n\n{txt}")
        out.append({k: r.get(k, "") for k in ["token", "variant", "segment", "company", "name", "email", "email_source", "email_source_date",
                                               "own_record", "status", "hold_reason"]} | {"drafted_on": TODAY, "sent_on": "", "reply_kind": "", "reply_on": "",
                                                                                         "facility_id": r["facility_id"], "page_url": link})
    with (R1 / "ledger.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    from collections import Counter
    print(len(out), "drafted", Counter((r["segment"], r["variant"]) for r in out))


if __name__ == "__main__":
    main()
