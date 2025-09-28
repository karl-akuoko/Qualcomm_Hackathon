#!/usr/bin/env python3
"""
Build Manhattan bus stops (AI-ready) from MTA GTFS Static.

Usage:
  python build_manhattan_bus_stops.py \
    --gtfs /path/to/nyct_bus.zip \
    --gtfs /path/to/mtabus.zip \
    --out-geojson manhattan_bus_stops.geojson \
    --out-csv manhattan_bus_stops.csv
"""
import argparse, json, zipfile, datetime, csv
from typing import List, Dict
import pandas as pd

def read_gtfs_tables(zip_path: str, names: List[str]) -> Dict[str, pd.DataFrame]:
    out = {}
    with zipfile.ZipFile(zip_path, 'r') as z:
        for n in names:
            try:
                with z.open(n) as f:
                    out[n] = pd.read_csv(f)
            except KeyError:
                out[n] = pd.DataFrame()
    return out

def load_feed_meta(zip_path: str) -> Dict[str,str]:
    meta = {"path": zip_path, "feed_publisher_name": None, "feed_version": None, "feed_start_date": None, "feed_end_date": None}
    with zipfile.ZipFile(zip_path, 'r') as z:
        try:
            with z.open('feed_info.txt') as f:
                fi = pd.read_csv(f)
                if not fi.empty:
                    r = fi.iloc[0].to_dict()
                    meta["feed_publisher_name"] = r.get("feed_publisher_name")
                    meta["feed_version"] = r.get("feed_version") or r.get("feed_version", None)
                    meta["feed_start_date"] = str(r.get("feed_start_date")) if "feed_start_date" in r else None
                    meta["feed_end_date"] = str(r.get("feed_end_date")) if "feed_end_date" in r else None
        except KeyError:
            pass
    return meta

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gtfs", action="append", required=True, help="Path to a GTFS Static zip (can pass multiple)")
    ap.add_argument("--out-geojson", required=True, help="Output GeoJSON path")
    ap.add_argument("--out-csv", required=True, help="Output CSV path")
    args = ap.parse_args()

    gtfs_tables = ["routes.txt","trips.txt","stop_times.txt","stops.txt"]
    feeds_meta = []
    rows = []

    for zp in args.gtfs:
        feeds_meta.append(load_feed_meta(zp))
        tbl = read_gtfs_tables(zp, gtfs_tables)
        routes = tbl["routes.txt"]
        trips = tbl["trips.txt"]
        stop_times = tbl["stop_times.txt"]
        stops = tbl["stops.txt"]

        # Filter Manhattan routes by short name starting with 'M' (case-insensitive)
        mroutes = routes[routes["route_short_name"].astype(str).str.upper().str.startswith("M", na=False)].copy()
        if mroutes.empty:
            continue

        mt = trips.merge(mroutes[["route_id","route_short_name"]], on="route_id", how="inner")
        st = stop_times.merge(mt[["trip_id","route_short_name"]], on="trip_id", how="inner")

        stop_to_routes = (st.groupby("stop_id")["route_short_name"]
                            .apply(lambda s: sorted(set([str(x) for x in s])))
                            .reset_index())

        merged = stop_to_routes.merge(stops, on="stop_id", how="left")

        for _, r in merged.iterrows():
            rows.append({
                "stop_id": str(r.get("stop_id")),
                "stop_code": str(r.get("stop_code")) if pd.notna(r.get("stop_code")) else None,
                "stop_name": r.get("stop_name"),
                "lat": float(r.get("stop_lat")) if pd.notna(r.get("stop_lat")) else None,
                "lon": float(r.get("stop_lon")) if pd.notna(r.get("stop_lon")) else None,
                "wheelchair_boarding": int(r.get("wheelchair_boarding")) if "wheelchair_boarding" in merged.columns and pd.notna(r.get("wheelchair_boarding")) else None,
                "routes_served": r.get("route_short_name"),
                "zone_id": r.get("zone_id") if "zone_id" in merged.columns and pd.notna(r.get("zone_id")) else None
            })

    # Deduplicate by stop_id, merge routes
    by_id: Dict[str, Dict] = {}
    for s in rows:
        sid = s["stop_id"]
        if sid not in by_id:
            by_id[sid] = s
            by_id[sid]["routes_served"] = list(s["routes_served"]) if isinstance(s["routes_served"], list) else []
        else:
            rs = by_id[sid]["routes_served"]
            for r in (s["routes_served"] or []):
                if r not in rs:
                    rs.append(r)

    # GEOJSON
    features = []
    for s in by_id.values():
        if s["lat"] is None or s["lon"] is None:
            continue
        props = s.copy()
        routes_csv = "|".join(props.pop("routes_served", []))
        props["routes_served_csv"] = routes_csv
        features.append({
            "type":"Feature",
            "geometry":{"type":"Point","coordinates":[s["lon"], s["lat"]]},
            "properties": props
        })
    geojson = {
        "type":"FeatureCollection",
        "name":"manhattan_bus_stops",
        "generated_at": datetime.datetime.now().astimezone().isoformat(),
        "features": features
    }
    with open(args.out-geojson, "w") as f:
        json.dump(geojson, f, indent=2)

    # CSV
    fieldnames = ["stop_id","stop_code","stop_name","lat","lon","wheelchair_boarding","routes_served_csv","zone_id"]
    with open(args.out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for s in by_id.values():
            if s["lat"] is None or s["lon"] is None:
                continue
            w.writerow({
                "stop_id": s["stop_id"],
                "stop_code": s["stop_code"],
                "stop_name": s["stop_name"],
                "lat": s["lat"],
                "lon": s["lon"],
                "wheelchair_boarding": s["wheelchair_boarding"],
                "routes_served_csv": "|".join(s["routes_served"] or []),
                "zone_id": s["zone_id"]
            })

    print(f"Wrote {len(features)} stops to {args.out_geojson} and CSV to {args.out_csv}")
if __name__ == "__main__":
    main()
