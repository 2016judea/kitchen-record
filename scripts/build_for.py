#!/usr/bin/env python3
"""site/for.json: recipient token -> {id, variant} from the (gitignored) outreach ledger.

The /for/<token>/ page opens on that recipient's own restaurant and fires
va.track('preview_open', {variant}) so A/B splits without the variant appearing in the URL.
Only the token, the public licence id and the variant letter ship; never a name or an email.
"""
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "outreach" / "round1" / "ledger.csv"


def main():
    out = {}
    if LEDGER.exists():
        for r in csv.DictReader(LEDGER.open()):
            if r.get("token") and r.get("facility_id"):
                out[r["token"]] = {"id": r["facility_id"], "v": r.get("variant", "")}
    (ROOT / "site" / "for.json").write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print(f"for.json: {len(out)} tokens")


if __name__ == "__main__":
    main()
