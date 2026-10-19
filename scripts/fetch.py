#!/usr/bin/env python3
"""Pull the City of Minneapolis Food_Inspections layer (open public record) into data/.

    python scripts/fetch.py            # today's pull, cached per day under data/cache/food/<date>/
    python scripts/fetch.py --refresh  # ignore today's cache

ArcGIS hands back at most 2,000 rows per call and says so with exceededTransferLimit, so
we page on resultOffset until it stops. Output: data/inspections.parquet (one row per
violation line; an inspection with no violations is one row with null violation fields).
"""
import json, sys, time
from datetime import date
from pathlib import Path
import duckdb, requests

ROOT = Path(__file__).resolve().parent.parent
URL = "https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/Food_Inspections/FeatureServer/0/query"
PAGE = 2000


def pull(day: str, refresh: bool) -> list[dict]:
    cache = ROOT / "data" / "cache" / "food" / day
    cache.mkdir(parents=True, exist_ok=True)
    rows, offset, n = [], 0, 0
    while True:
        f = cache / f"page_{n:03d}.json"
        if f.exists() and not refresh:
            j = json.loads(f.read_text())
        else:
            for attempt in range(5):
                try:
                    r = requests.get(URL, params={"where": "1=1", "outFields": "*", "returnGeometry": "false", "f": "json",
                                                  "orderByFields": "OBJECTID", "resultOffset": offset, "resultRecordCount": PAGE}, timeout=90)
                    j = r.json()
                    if "features" in j:
                        break
                except (requests.RequestException, ValueError):
                    pass
                time.sleep(3 * (attempt + 1))
            else:
                sys.exit(f"page {n} failed")
            f.write_text(json.dumps(j))
        feats = [x["attributes"] for x in j.get("features", [])]
        rows += feats
        print(f"page {n}: {len(feats)} rows (total {len(rows)})", flush=True)
        if not j.get("exceededTransferLimit") or not feats:
            break
        offset += len(feats)
        n += 1
    return rows


def write(rows: list[dict]) -> None:
    out = ROOT / "data" / "inspections.parquet"
    out.parent.mkdir(exist_ok=True)
    tmp = ROOT / "data" / "_rows.json"
    tmp.write_text(json.dumps(rows))
    con = duckdb.connect()
    con.execute(f"""
      copy (
        select OBJECTID::bigint as object_id,
               HealthFacilityIDNumber as facility_id, trim(FacilityCategory) as category, trim(BusinessName) as name,
               RiskLevel as risk_level, trim(FullAddress) as address, ZipCode as zip, trim(Neighborhood) as neighbourhood, Ward as ward,
               Latitude as lat, Longitude as lon,
               InspectionIDNumber::bigint as inspection_id, InspectionType as inspection_type, InspectionResult as result,
               (to_timestamp(DateOfInspection / 1000) at time zone 'America/Chicago')::date as inspected_on, InspectionScore::int as score,
               ViolationIDNumber::bigint as violation_id, ViolationPriority as priority, FoodCodeItem as code, FoodCodeText as code_text,
               InspectorComments as comment, ViolationStatus as status, ViolationPoints::int as points, APN as apn
        from read_json('{tmp}', maximum_object_size=200000000)
      ) to '{out}' (format parquet)""")
    tmp.unlink()
    print(con.execute(f"select count(*), count(distinct facility_id), min(inspected_on), max(inspected_on) from '{out}'").fetchall())


if __name__ == "__main__":
    day = date.today().isoformat()
    rows = pull(day, "--refresh" in sys.argv)
    write(rows)
    (ROOT / "data" / "pulled_on.txt").write_text(day + "\n")
