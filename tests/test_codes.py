import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from codes import CODES, lookup  # noqa: E402


def test_every_hand_written_code_has_all_four_fields():
    for code, c in CODES.items():
        assert set(c) == {"short", "plain", "checks", "fix"}, code
        assert all(c[k].strip() for k in c), code


def test_unknown_code_falls_back_to_the_citys_text():
    r = lookup("MN Rule 4626.9999", "Floors must be smooth. And cleanable.")
    assert r == {"short": "Floors must be smooth", "plain": "Floors must be smooth. And cleanable.",
                 "checks": r["checks"], "fix": r["fix"], "hand_written": False}
    assert lookup("MN Rule 4626.9999", None)["plain"] == "MN Rule 4626.9999"
    assert lookup("MN Rule 4626.0395A2", None)["hand_written"] is True


def test_inspection_date_is_the_minneapolis_day_whatever_the_machine_timezone():
    # 1792200600 s == 2026-10-17 01:30 UTC == 2026-10-16 20:30 CDT
    con = duckdb.connect()
    con.execute("set TimeZone='UTC'")
    got = con.execute("select strftime((to_timestamp(1792200600000 / 1000) at time zone 'America/Chicago')::date, '%Y-%m-%d'), strftime(to_timestamp(1792200600000 / 1000)::date, '%Y-%m-%d')").fetchone()
    assert got == ("2026-10-16", "2026-10-17"), "the bare cast follows the machine's zone; the pinned one does not"
    assert "at time zone 'America/Chicago'" in (Path(__file__).resolve().parent.parent / "scripts/fetch.py").read_text()
