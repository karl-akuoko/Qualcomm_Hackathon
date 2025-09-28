#!/usr/bin/env python3
"""
Build Manhattan route list (AI-ready). Optionally get live vehicle counts via SIRI.

Usage:
  python build_manhattan_routes_and_counts.py \
    --gtfs /path/to/nyct_bus.zip \
    --gtfs /path/to/mtabus.zip \
    --out manhattan_routes.json \
    [--siri-key YOUR_MTA_API_KEY]

If --siri-key is given, the script will try to fetch VehicleMonitoring counts per
route (internet required). Without it, it emits the static route list.
"""
import argparse, json, zipfile, datetime, os, sys
from typing import List, Dict
import pandas as pd

def read_routes(zip_path: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path, 'r') as z:
        with z.open('routes.txt') as f:
            return pd.read_csv(f)

def unique_routes(gtfs_paths: List[str]) -> pd.DataFrame:
    dfs = []
    for p in gtfs_paths:
        try:
            dfs.append(read_routes(p))
        except KeyError:
            pass
    if not dfs:
        return pd.DataFrame(columns=["route_id","route_short_name","route_long_name","agency_id"])
    routes = pd.concat(dfs, ignore_index=True)
    routes["route_short_name"] = routes["route_short_name"].astype(str)
    m = routes[routes["route_short_name"].str.upper().str.startswith("M", na=False)].copy()
    # Dedup by short name
    m = m.sort_values("route_short_name").drop_duplicates(subset=["route_short_name"])
    keep = ["route_id","route_short_name","route_long_name","agency_id"]
    for k in keep:
        if k not in m.columns:
            m[k] = None
    return m[keep]

def siri_vehicle_count(line_ref: str, api_key: str) -> int:
    import requests
    url = "https://bustime.mta.info/api/siri/vehicle-monitoring.json"
    params = {"key": api_key, "LineRef": line_ref}
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    acts = (data.get("Siri",{})
                .get("ServiceDelivery",{})
                .get("VehicleMonitoringDelivery",[{}])[0]
                .get("VehicleActivity",[]))
    return len(acts)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gtfs", action="append", required=True, help="Path to GTFS Static zip (can pass multiple)")
    ap.add_argument("--out", required=True, help="Output JSON path")
    ap.add_argument("--siri-key", help="MTA Bus Time API key for live vehicle counts (optional)")
    args = ap.parse_args()

    routes_df = unique_routes(args.gtfs)
    routes = []
    for _, r in routes_df.iterrows():
        routes.append({
            "route_short_name": r["route_short_name"],
            "route_id": r.get("route_id"),
            "route_long_name": r.get("route_long_name"),
            "agency_id": r.get("agency_id"),
            "live_active_vehicles": None
        })

    # optionally enrich with live counts
    if args.siri_key:
        for item in routes:
            try:
                item["live_active_vehicles"] = siri_vehicle_count(item["route_short_name"], args.siri_key)
            except Exception as e:
                item["live_active_vehicles"] = None

    payload = {
        "generated_at": datetime.datetime.now().astimezone().isoformat(),
        "borough": "Manhattan",
        "routes": routes
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {len(routes)} routes to {args.out}")
if __name__ == "__main__":
    main()
