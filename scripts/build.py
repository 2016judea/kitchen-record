#!/usr/bin/env python3
"""Build the model from data/inspections.parquet.

Writes
  site/public/data/free.json      the free slice for every restaurant (score history, neighbourhood
                           p10/50/90, most-repeated Priority-1 code in plain words, counts only
                           for the paid part) plus the lookup index
  site/public/meta.json         counts, dates, price, the example restaurant
  private/bundle/full.json.gz   the paid part, keyed by restaurant id: fix list, follow-up risk,
                           named peer table (served only by /api/data)
  data/model.duckdb        the tables, for tests and QA

Every number on the page comes from here; nothing is typed into the HTML.
"""
import gzip, json, sys
from datetime import date
from pathlib import Path
import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codes import lookup  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OFFER = json.loads((ROOT / "site" / "offer.json").read_text())
MIN_PEERS = 15          # a neighbourhood with fewer restaurants shows the city spread, labelled
FU_WINDOW = 45          # days after a routine inspection in which a Follow-Up counts as caused by it
CITY_RULE_SCORE = 91    # minneapolismn.gov: a follow-up is done at 91 points or lower


def build(parquet: Path, out_db: Path | None = None) -> dict:
    con = duckdb.connect(str(out_db) if out_db else ":memory:")
    if out_db:
        for t in ("v", "insp", "rest", "nb", "rep"):
            con.execute(f"drop table if exists {t}")
    con.execute(f"create table v as select * from read_parquet('{parquet}') where category = 'RESTAURANT'")
    con.execute("""create table insp as
      select facility_id, inspection_id, inspection_type, inspected_on, max(score) score,
             count(*) filter (where priority='Priority1') p1, count(*) filter (where priority='Priority2') p2,
             count(*) filter (where priority='Priority3') p3
      from v group by all""")
    con.execute("""create table rest as
      select facility_id id, arg_max(name, inspected_on) as "name", arg_max(address, inspected_on) as address,
             coalesce(arg_max(neighbourhood, inspected_on), 'No neighbourhood on file') nb, arg_max(risk_level, inspected_on) risk,
             arg_max(lat, inspected_on) lat, arg_max(lon, inspected_on) lon, arg_max(zip, inspected_on) zip
      from v group by 1""")
    # neighbourhood spread: every routine inspection of every restaurant there
    con.execute(f"""create table nb as
      select r.nb, count(distinct r.id) n_rest, count(*) n_insp,
             quantile_cont(i.score, 0.1) p10, quantile_cont(i.score, 0.5) p50, quantile_cont(i.score, 0.9) p90,
             avg(case when i.p1 > 0 then 1 else 0 end) p1_rate
      from insp i join rest r on r.id = i.facility_id where i.inspection_type = 'Routine' group by 1""")
    city = con.execute("""select count(distinct facility_id), count(*), quantile_cont(score,0.1), quantile_cont(score,0.5), quantile_cont(score,0.9),
                                 avg(case when p1>0 then 1 else 0 end) from insp where inspection_type='Routine'""").fetchone()
    # repeated Priority-1 codes: same code on >= 2 distinct inspections of the same restaurant
    con.execute("""create table rep as
      select facility_id, code, min(code_text) code_text, count(distinct inspection_id) times, max(inspected_on) last_on,
             list(distinct inspection_id) insp_ids
      from v where priority = 'Priority1' and code is not null group by 1, 2 having count(distinct inspection_id) >= 2""")
    # the follow-up rule, measured: share of routine inspections followed by a Follow-Up within FU_WINDOW days, by score band
    fu = dict(con.execute(f"""
      with r as (select * from insp where inspection_type='Routine' and inspected_on < (select max(inspected_on) from insp) - interval '{FU_WINDOW} days'),
           f as (select facility_id, inspected_on fu from insp where inspection_type='Follow-Up')
      select case when score <= {CITY_RULE_SCORE} then 'le' else 'gt' end band,
             avg(case when exists (select 1 from f where f.facility_id=r.facility_id and f.fu > r.inspected_on and f.fu <= r.inspected_on + interval '{FU_WINDOW} days') then 1 else 0 end)
      from r group by 1""").fetchall())
    code_n = {c: (f, h) for c, f, h in con.execute("select code, count(distinct facility_id), count(*) from v where priority='Priority1' and code is not null group by 1").fetchall()}

    nbd = {r[0]: {"n": r[1], "n_insp": r[2], "p10": r[3], "p50": r[4], "p90": r[5], "p1_rate": round(r[6], 3)} for r in con.execute("select * from nb").fetchall()}
    hist = {}
    for fid, iid, typ, d, sc, p1, p2, p3 in con.execute("select facility_id, inspection_id, inspection_type, inspected_on, score, p1, p2, p3 from insp order by inspected_on, inspection_id").fetchall():
        hist.setdefault(fid, []).append({"id": iid, "t": {"Routine": "R", "Follow-Up": "F"}.get(typ, "V"), "d": d.isoformat(), "s": sc, "p1": p1, "p2": p2, "p3": p3})
    reps = {}
    for fid, code, txt, times, last_on, ids in con.execute("select * from rep order by times desc, last_on desc").fetchall():
        reps.setdefault(fid, []).append({"code": code, "code_text": txt, "times": times, "last": last_on.isoformat(), "insp_ids": ids})
    comments = {}
    for fid, code, iid, d, cm, st in con.execute("select facility_id, code, inspection_id, inspected_on, comment, status from v where priority='Priority1' and code is not null order by inspected_on desc").fetchall():
        comments.setdefault((fid, code), []).append({"d": d.isoformat(), "c": (cm or "").strip(), "status": st})

    rows, full = [], {}
    rests = con.execute("select * from rest order by name").fetchall()
    by_nb = {}
    for r in rests:
        by_nb.setdefault(r[3], []).append(r)
    for rid, name, address, nb, risk, lat, lon, zip_ in rests:
        h = hist.get(rid, [])
        routine = [x for x in h if x["t"] == "R"]
        fus = [x for x in h if x["t"] == "F"]
        last = routine[-1] if routine else None
        rp = reps.get(rid, [])
        top = rp[0] if rp else None
        peer = nbd.get(nb) if nbd.get(nb, {}).get("n", 0) >= MIN_PEERS else None
        # free slice
        rows.append({
            "id": rid, "name": name, "address": address, "nb": nb, "risk_level": risk, "lat": lat, "lon": lon,
            "hist": [{"d": x["d"], "s": x["s"], "p1": x["p1"], "t": x["t"]} for x in h],
            "top": ({"code": top["code"], "short": lookup(top["code"], top["code_text"])["short"],
                     "plain": lookup(top["code"], top["code_text"])["plain"], "times": top["times"], "last": top["last"],
                     "n_city": code_n.get(top["code"], (0, 0))[0]} if top else None),
            "n_rep": len(rp), "n_fu": len(fus), "last": ({"d": last["d"], "s": last["s"], "p1": last["p1"]} if last else None),
        })
        # paid part
        fix = []
        for x in rp:
            lk = lookup(x["code"], x["code_text"])
            fix.append({"code": x["code"], "short": lk["short"], "plain": lk["plain"], "checks": lk["checks"], "fix": lk["fix"],
                        "times": x["times"], "last": x["last"], "n_city": code_n.get(x["code"], (0, 0))[0],
                        "comments": [c for c in comments.get((rid, x["code"]), []) if c["c"]][:4]})
        # follow-up risk: the city's rule applied to the last score, the measured rate for that band,
        # and what the score would be if every repeated P1 line were written again
        proj = 100 - 4 * len(rp)
        risk_block = None
        if last:
            band = "le" if last["s"] <= CITY_RULE_SCORE else "gt"
            risk_block = {"last_score": last["s"], "last_date": last["d"], "rule": CITY_RULE_SCORE, "band": band,
                          "rate": round(fu.get(band, 0), 3), "rate_le": round(fu.get("le", 0), 3), "rate_gt": round(fu.get("gt", 0), 3),
                          "window_days": FU_WINDOW, "n_followups": len(fus), "n_routine": len(routine),
                          "if_repeated_score": proj, "if_repeated_followup": proj <= CITY_RULE_SCORE}
        peers = []
        for pr in by_nb.get(nb, []):
            ph = [x for x in hist.get(pr[0], []) if x["t"] == "R"]
            if not ph:
                continue
            pl = ph[-1]
            peers.append({"id": pr[0], "name": pr[1], "address": pr[2], "last_score": pl["s"], "last_date": pl["d"], "p1": pl["p1"],
                          "n_rep": len(reps.get(pr[0], [])), "n_fu": len([x for x in hist.get(pr[0], []) if x["t"] == "F"]), "me": pr[0] == rid})
        peers.sort(key=lambda p: (-p["last_score"], p["name"]))
        full[rid] = {"fix": fix, "risk": risk_block, "peers": peers, "peer_set": nb if peer else "Minneapolis", "n_peers": len(peers)}

    # the example the page opens on: most repeated P1 codes among restaurants with >= 5 routine
    # inspections in a neighbourhood with a real peer set; ties broken by the latest inspection
    cands = [r for r in rows if len([x for x in r["hist"] if x["t"] == "R"]) >= 4 and r["nb"] in nbd and nbd[r["nb"]]["n"] >= MIN_PEERS and r["n_rep"] >= 2]
    cands.sort(key=lambda r: (-r["n_rep"], -(r["last"]["s"] <= CITY_RULE_SCORE), r["hist"][-1]["d"]), reverse=False)
    example = cands[0]["id"] if cands else rows[0]["id"]

    pulled = (ROOT / "data" / "pulled_on.txt").read_text().strip() if (ROOT / "data" / "pulled_on.txt").exists() else date.today().isoformat()
    first, lastd = con.execute("select min(inspected_on), max(inspected_on) from insp").fetchone()
    meta = {
        "built": date.today().isoformat(), "pulled_on": pulled, "first": first.isoformat(), "last": lastd.isoformat(),
        "n_restaurants": city[0], "n_routine": city[1], "city": {"p10": city[2], "p50": city[3], "p90": city[4], "p1_rate": round(city[5], 3)},
        "n_repeat": sum(1 for r in rows if r["n_rep"] > 0), "n_nb": sum(1 for n in nbd.values() if n["n"] >= MIN_PEERS),
        "rule_score": CITY_RULE_SCORE, "fu_window": FU_WINDOW, "fu_rate_le": round(fu.get("le", 0), 3), "fu_rate_gt": round(fu.get("gt", 0), 3),
        "min_peers": MIN_PEERS, "example": example, "price_usd": OFFER["price_usd"], "product": OFFER["product"],
        "codes_hand_written": sum(1 for r in rows if r["top"] and lookup(r["top"]["code"], None)["hand_written"]),
    }
    free = {"meta": meta, "nb": {k: v for k, v in nbd.items() if v["n"] >= MIN_PEERS}, "rows": rows}
    return {"free": free, "full": full, "meta": meta}


PAID_KEYS = {"fix", "risk", "peers"}  # never in free.json (tests/test_paywall.py)


def main():
    out = build(ROOT / "data" / "inspections.parquet", ROOT / "data" / "model.duckdb")
    (ROOT / "site" / "public" / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / "private" / "bundle").mkdir(parents=True, exist_ok=True)
    (ROOT / "site" / "public" / "data" / "free.json").write_text(json.dumps(out["free"], separators=(",", ":")))
    (ROOT / "site" / "public" / "meta.json").write_text(json.dumps(out["meta"], indent=1))
    with gzip.open(ROOT / "private" / "bundle" / "full.json.gz", "wt") as f:
        json.dump(out["full"], f, separators=(",", ":"))
    m = out["meta"]
    print(f"{m['n_restaurants']} restaurants, {m['n_routine']} routine inspections {m['first']}..{m['last']}; "
          f"{m['n_repeat']} repeat a P1 code; {m['n_nb']} neighbourhoods with >= {MIN_PEERS}; "
          f"follow-up within {FU_WINDOW}d: {m['fu_rate_le']:.1%} at <= {CITY_RULE_SCORE}, {m['fu_rate_gt']:.1%} above; example {m['example']}")
    print("free.json", (ROOT / "site" / "public" / "data" / "free.json").stat().st_size // 1024, "KB; full.json.gz", (ROOT / "private" / "bundle" / "full.json.gz").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
