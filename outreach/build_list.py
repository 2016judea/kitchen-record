#!/usr/bin/env python3
"""Round-1 recipient list: Minneapolis restaurants whose own public listing carries an email,
matched to their own inspection row by street address. Writes outreach/round1/candidates.csv
(gitignored) for the drafter. Nothing here sends anything.

Sources (read-only):
  ~/Desktop/bricks/data/cache/overture_places_msp.parquet   Overture Places (CC BY 4.0): emails[], websites[]
  ~/Desktop/bricks/data/mail_list_with_emails.csv           the May 2026 mailer list (21 restaurant emails)
  data/model.duckdb                                         this repo's model (restaurants, scores, repeats)
Dedupe: ~/Desktop/outreach-ledger/outreach.duckdb `contacted` (mandatory, outreach-ledger skill).
"""
import csv, re
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
DESK = Path.home() / "Desktop"
OUT = ROOT / "outreach" / "round1" / "candidates.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

SUFFIX = {"STREET": "ST", "AVENUE": "AVE", "BOULEVARD": "BLVD", "ROAD": "RD", "DRIVE": "DR", "LANE": "LN", "PARKWAY": "PKWY",
          "PLACE": "PL", "COURT": "CT", "TERRACE": "TER", "HIGHWAY": "HWY", "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
          "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW"}
BAD_EMAIL = re.compile(r"\.(png|jpg|jpeg|gif|svg|webp)$|@2x|example\.com|sentry|wixpress|godaddy|squarespace|@email\.com|noreply|no-reply", re.I)


def norm_addr(a: str) -> str:
    a = re.sub(r"[^A-Z0-9 ]", " ", (a or "").upper())
    a = re.sub(r"\b(SUITE|STE|UNIT|APT|#)\s*\w+\b", " ", a)
    toks = [SUFFIX.get(t, t) for t in a.split()]
    # house number + first two street tokens is enough to match within a city
    return " ".join(toks[:3])


def main():
    con = duckdb.connect(str(ROOT / "data" / "model.duckdb"), read_only=True)
    rest = con.execute("select id, name, address, nb from rest").fetchall()
    by_addr = {}
    for rid, name, addr, nb in rest:
        by_addr.setdefault(norm_addr(addr), []).append((rid, name, addr, nb))

    o = duckdb.connect()
    ov = o.execute(f"""select name, addr, emails, websites, category from read_parquet('{DESK}/bricks/data/cache/overture_places_msp.parquet')
                        where lower(city) = 'minneapolis' and len(emails) > 0""").fetchall()
    cands = {}
    for name, addr, emails, sites, cat in ov:
        k = norm_addr(addr)
        if k not in by_addr:
            continue
        for rid, rname, raddr, nb in by_addr[k]:
            # same address AND a name token in common, so a food hall's tenants don't all get one email
            nt = set(re.findall(r"[A-Z]{3,}", (name or "").upper())) & set(re.findall(r"[A-Z]{3,}", rname.upper()))
            if not nt and len(by_addr[k]) > 1:
                continue
            for e in emails:
                e = e.strip().lower()
                if "@" not in e or BAD_EMAIL.search(e):
                    continue
                cands.setdefault(rid, {"facility_id": rid, "company": rname, "address": raddr, "nb": nb, "email": e,
                                       "email_source": f"Overture Places listing for {name} ({(sites or [''])[0]})", "email_source_date": "2026-08 (Overture release in bricks cache)", "segment": "restaurant"})
                break
    ml = DESK / "bricks" / "data" / "mail_list_with_emails.csv"
    for r in csv.DictReader(ml.open()):
        if r["Sector"] != "Restaurant" or not r["Email"] or BAD_EMAIL.search(r["Email"]):
            continue
        k = norm_addr(r["Street Address"])
        for rid, rname, raddr, nb in by_addr.get(k, []):
            cands.setdefault(rid, {"facility_id": rid, "company": rname, "address": raddr, "nb": nb, "email": r["Email"].lower(),
                                   "email_source": f"own website {r['Website']} (May 2026 mailer list)", "email_source_date": "2026-05", "segment": "restaurant"})
    # dedupe against every past send (mandatory)
    led = duckdb.connect(str(DESK / "outreach-ledger" / "outreach.duckdb"), read_only=True)
    contacted = {r[0] for r in led.execute("select recipient_key from contacted").fetchall()}
    rows = [c for c in cands.values() if c["email"] not in contacted]
    dropped = len(cands) - len(rows)
    # own-record fields for the opener
    free = {r[0]: r for r in con.execute("""select facility_id, max(inspected_on), arg_max(score, inspected_on) from insp where inspection_type='Routine' group by 1""").fetchall()}
    reps = {}
    for fid, code, times, last in con.execute("select facility_id, code, times, last_on from rep order by times desc, last_on desc").fetchall():
        reps.setdefault(fid, (code, times, last))
    for c in rows:
        f = free.get(c["facility_id"])
        c["last_date"], c["last_score"] = (f[1].isoformat(), f[2]) if f else ("", "")
        rp = reps.get(c["facility_id"])
        c["rep_code"], c["rep_times"], c["rep_last"] = (rp[0], rp[1], rp[2].isoformat()) if rp else ("", "", "")
    rows.sort(key=lambda c: (-(c["rep_times"] or 0), c["last_score"] or 101))
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"{len(cands)} restaurants with an email matched to their own inspection row; {dropped} already contacted (dropped); {len(rows)} candidates -> {OUT}")
    print(f"  with a repeated P1 line: {sum(1 for c in rows if c['rep_code'])}; last score <= 91: {sum(1 for c in rows if c['last_score'] and c['last_score'] <= 91)}")


if __name__ == "__main__":
    main()
