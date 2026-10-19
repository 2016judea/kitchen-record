"""The free slice never leaks a paid field; the paid bundle holds them all; the gitignore holds."""
import gzip, json, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build import PAID_KEYS  # noqa: E402

FREE = ROOT / "site" / "public" / "data" / "free.json"
FULL = ROOT / "private" / "bundle" / "full.json.gz"
pytestmark = pytest.mark.skipif(not (FREE.exists() and FULL.exists()), reason="run scripts/build.py first")


def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


def test_free_slice_has_no_paid_keys():
    free = json.loads(FREE.read_text())
    keys = set(walk(free["rows"]))
    assert not (keys & PAID_KEYS), keys & PAID_KEYS
    for r in free["rows"]:
        assert set(r) <= {"id", "name", "address", "nb", "risk_level", "lat", "lon", "hist", "top", "n_rep", "n_fu", "last"}
        if r["top"]:
            assert set(r["top"]) <= {"code", "short", "plain", "times", "last", "n_city"}  # no checks/fix for free
    text = FREE.read_text()
    assert "Inspector checks" not in text and '"checks"' not in text and '"peers"' not in text


def test_full_bundle_has_the_paid_part():
    full = json.load(gzip.open(FULL, "rt"))
    free = json.loads(FREE.read_text())
    assert set(full) == {r["id"] for r in free["rows"]}
    some = [d for d in full.values() if d["fix"]]
    assert len(some) > 500
    assert all(PAID_KEYS <= set(d) for d in full.values())


def test_paid_bundle_is_not_in_site_or_git():
    assert not (ROOT / "site" / "api" / "_full").exists()
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    assert not any(p.startswith("private/") or p.startswith("outreach/round1/") or p.startswith("data/cache") for p in tracked), tracked
    assert "site/public/data/free.json" in tracked or not tracked  # before the first commit the list is empty


def test_only_site_public_is_served_statically():
    # With outputDirectory "." Vercel served every uploaded file, so /api/%5Ffull/full.json.gz
    # handed out the paid bundle (proven by curl on production, 2026-10-19). Pin both halves.
    vj = json.loads((ROOT / "site" / "vercel.json").read_text())
    assert vj["outputDirectory"] == "public"
    assert '"outputDirectory": "public"' in (ROOT / "scripts" / "deploy.py").read_text()
    pub = ROOT / "site" / "public"
    assert (pub / "index.html").exists() and (pub / "data" / "free.json").exists()
    assert not any(p.suffix == ".gz" or "_full" in p.parts or p.name == "_lib.js" for p in pub.rglob("*"))


def test_for_json_carries_only_token_id_and_variant():
    fj = json.loads((ROOT / "site" / "public" / "for.json").read_text())
    free_ids = {r["id"] for r in json.loads(FREE.read_text())["rows"]}
    for t, v in fj.items():
        assert set(v) <= {"id", "v"} and v["id"] in free_ids and v.get("v", "") in ("", "A", "B")
    assert "@" not in (ROOT / "site" / "public" / "for.json").read_text()
