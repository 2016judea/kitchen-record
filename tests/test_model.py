"""The model loader and the page build, against the real pull in data/ (skips if it is absent)."""
import gzip, json, re, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build import build, CITY_RULE_SCORE, MIN_PEERS  # noqa: E402
from codes import CODES, lookup  # noqa: E402

PARQUET = ROOT / "data" / "inspections.parquet"
pytestmark = pytest.mark.skipif(not PARQUET.exists(), reason="run scripts/fetch.py first")


@pytest.fixture(scope="module")
def out():
    return build(PARQUET)


def test_rows_are_restaurants_with_history(out):
    rows = out["free"]["rows"]
    assert len(rows) > 1000
    assert all(r["id"].startswith("LIC") for r in rows)
    assert all(len(r["hist"]) >= 1 for r in rows)
    assert all(r["nb"] for r in rows)


def test_score_is_the_citys_arithmetic(out):
    # 100 - 4 per Priority-1 - 2 per Priority-2 on the great majority of routine visits
    # (the city's page: "Violations receive either zero, two or four points each")
    import duckdb
    con = duckdb.connect()
    ok, n = con.execute(f"""with i as (select inspection_id, max(score) s,
        count(*) filter (where priority='Priority1') p1, count(*) filter (where priority='Priority2') p2
        from read_parquet('{PARQUET}') where inspection_type='Routine' group by 1)
        select avg(case when s = 100 - 4*p1 - 2*p2 then 1 else 0 end), count(*) from i""").fetchone()
    assert n > 5000 and ok > 0.95


def test_neighbourhood_spread_exists(out):
    nb = out["free"]["nb"]
    assert len(nb) >= 20
    for k, v in nb.items():
        assert v["n"] >= MIN_PEERS
        assert v["p10"] <= v["p50"] <= v["p90"] <= 100
    city = out["meta"]["city"]
    assert city["p90"] - city["p10"] >= 10, "a comparison with no spread is a tool with no answer"


def test_repeated_codes_are_repeats(out):
    full = out["full"]
    for rid, d in list(full.items())[:400]:
        for x in d["fix"]:
            assert x["times"] >= 2
            assert x["checks"] and x["fix"] and x["plain"]
    tops = [r["top"] for r in out["free"]["rows"] if r["top"]]
    assert len(tops) > 500
    hand = sum(1 for t in tops if t["code"] in CODES)
    assert hand / len(tops) > 0.95, "the hand-written dictionary should cover nearly every most-repeated code"


def test_followup_rule_measured(out):
    m = out["meta"]
    assert m["rule_score"] == CITY_RULE_SCORE == 91
    assert m["fu_rate_le"] > 0.7 and m["fu_rate_gt"] < 0.1
    rows = {r["id"]: r for r in out["free"]["rows"]}
    for rid, d in out["full"].items():
        k = d["risk"]
        if not k:
            continue
        assert k["band"] == ("le" if k["last_score"] <= 91 else "gt")
        assert k["if_repeated_score"] == 100 - 4 * len(d["fix"])


def test_peers_are_named_and_include_me(out):
    for rid, d in list(out["full"].items())[:300]:
        assert any(p["me"] for p in d["peers"]), rid
        scores = [p["last_score"] for p in d["peers"]]
        assert scores == sorted(scores, reverse=True)


def test_example_opens_on_a_real_repeat_case(out):
    ex = out["meta"]["example"]
    r = next(r for r in out["free"]["rows"] if r["id"] == ex)
    assert r["n_rep"] >= 2 and r["nb"] in out["free"]["nb"]


def test_codes_dictionary_is_plain():
    for code, c in CODES.items():
        assert code.startswith("MN Rule 4626.")
        for k in ("plain", "checks", "fix"):
            assert 30 < len(c[k]) < 420, (code, k)
    fb = lookup("MN Rule 4626.9999", "Keep the cat out of the kitchen.")
    assert fb["plain"] == "Keep the cat out of the kitchen." and not fb["hand_written"]


def test_page_build_has_no_typed_numbers():
    html = (ROOT / "site" / "index.html").read_text()
    assert "_vercel/insights/script.js" in html
    assert "bm-posthog:begin" in html and 'site:S' in html and 'S="kitchen-record"' in html
    for ev in ("preview_open", "checkout_open", "paid", "unlock", "open_restaurant"):
        assert f'"{ev}"' in html or f"'{ev}'" in html
    # the price and the counts come from meta, never typed
    assert "M.price_usd" in html and "M.n_restaurants" in html
    assert not re.search(r"\$\d{2,}", html.replace("$$", "")), "a typed dollar figure in the page"
    assert "font:16px" in html  # iOS does not zoom a 16px input


def test_shipped_files_match_build(out):
    free = ROOT / "site" / "data" / "free.json"
    meta = ROOT / "site" / "meta.json"
    if not free.exists():
        pytest.skip("not built")
    shipped = json.loads(free.read_text())
    assert shipped["meta"]["n_restaurants"] == out["meta"]["n_restaurants"]
    assert json.loads(meta.read_text())["example"] == out["meta"]["example"]
    offer = json.loads((ROOT / "site" / "offer.json").read_text())
    assert offer["product"] == "kitchen-record" and offer["price_usd"] == shipped["meta"]["price_usd"]
