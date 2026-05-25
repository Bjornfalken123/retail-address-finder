#!/usr/bin/env python3
import argparse
import csv
import re
import sys
import time
from pathlib import Path

import requests

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

COUNTRY_TO_ISO = {
    "norway": ("NO", "Norway"),
    "norge": ("NO", "Norway"),
    "france": ("FR", "France"),
    "frankrike": ("FR", "France"),
    "belgium": ("BE", "Belgium"),
    "belgien": ("BE", "Belgium"),
    "netherlands": ("NL", "Netherlands"),
    "nederländerna": ("NL", "Netherlands"),
    "nederlanderna": ("NL", "Netherlands"),
    "sweden": ("SE", "Sweden"),
    "sverige": ("SE", "Sweden"),
    "denmark": ("DK", "Denmark"),
    "danmark": ("DK", "Denmark"),
    "finland": ("FI", "Finland"),
    "germany": ("DE", "Germany"),
    "tyskland": ("DE", "Germany"),
    "spain": ("ES", "Spain"),
    "spanien": ("ES", "Spain"),
    "italy": ("IT", "Italy"),
    "italien": ("IT", "Italy"),
}

def log(message: str) -> None:
    print(message, flush=True)

def safe_filename(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9åäöæøéüß]+", "_", value, flags=re.I)
    return value.strip("_") or "export"

def overpass_regex_for_chain(chain: str) -> str:
    """
    Escape regex special characters but DO NOT escape spaces.
    re.escape('REMA 1000') creates 'REMA\\ 1000', which can trigger Overpass 406 errors.
    """
    chain = chain.strip()
    escaped = re.sub(r"([.^$*+?{}\[\]\\|()])", r"\\\1", chain)
    escaped = re.sub(r"\s+", " ", escaped)
    return escaped

def build_query(country_iso: str, chain: str, mode: str) -> str:
    chain_regex = overpass_regex_for_chain(chain)

    if mode == "brand_shop":
        selector = f'["shop"~"supermarket|convenience|department_store|greengrocer"]["brand"~"{chain_regex}",i]'
    elif mode == "name_shop":
        selector = f'["shop"~"supermarket|convenience|department_store|greengrocer"]["name"~"{chain_regex}",i]'
    elif mode == "operator_shop":
        selector = f'["shop"~"supermarket|convenience|department_store|greengrocer"]["operator"~"{chain_regex}",i]'
    else:
        raise ValueError(f"Unknown mode: {mode}")

    return f"""
[out:json][timeout:120];
area["ISO3166-1"="{country_iso}"][admin_level=2]->.searchArea;
(
  node{selector}(area.searchArea);
  way{selector}(area.searchArea);
  relation{selector}(area.searchArea);
);
out tags center;
"""

def fetch_overpass(query: str) -> dict:
    last_error = None

    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(1, 3):
            try:
                log(f"Trying {endpoint} attempt {attempt}/2")
                response = requests.post(
                    endpoint,
                    data={"data": query},
                    timeout=180,
                    headers={
                        "User-Agent": "RetailAddressFinder/0.1 (GitHub Actions)",
                        "Accept": "application/json",
                    },
                )

                if response.status_code == 406:
                    preview = response.text[:600].replace("\n", " ")
                    raise RuntimeError(f"Overpass rejected query with 406. Response preview: {preview}")

                response.raise_for_status()
                return response.json()

            except Exception as exc:
                last_error = exc
                log(f"Failed: {type(exc).__name__}: {exc}")
                time.sleep(6 * attempt)

    raise RuntimeError(f"All Overpass endpoints failed. Last error: {last_error}")

def get_tag(tags: dict, *names: str) -> str:
    for name in names:
        value = tags.get(name)
        if value:
            return str(value).strip()
    return ""

def element_to_row(element: dict, country_name: str, chain: str) -> dict | None:
    tags = element.get("tags", {}) or {}

    street = get_tag(tags, "addr:street")
    housenumber = get_tag(tags, "addr:housenumber")
    postcode = get_tag(tags, "addr:postcode")
    city = get_tag(tags, "addr:city", "addr:town", "addr:village", "addr:municipality")
    full = get_tag(tags, "addr:full")

    if street and housenumber:
        street_line = f"{street} {housenumber}"
    else:
        street_line = street or full

    if not street_line or not postcode or not city:
        return None

    address_formatted = " ".join([street_line, postcode, city, country_name])

    return {
        "chain_requested": chain,
        "name": get_tag(tags, "name"),
        "brand": get_tag(tags, "brand"),
        "operator": get_tag(tags, "operator"),
        "street": street,
        "housenumber": housenumber,
        "postcode": postcode,
        "city": city,
        "country": country_name,
        "address_formatted": address_formatted,
        "osm_type": element.get("type", ""),
        "osm_id": element.get("id", ""),
        "source": "OpenStreetMap via Overpass API",
    }

def dedupe(rows: list[dict]) -> list[dict]:
    seen = set()
    unique = []

    for row in rows:
        key = (
            row.get("address_formatted", "").casefold(),
            row.get("name", "").casefold(),
            row.get("brand", "").casefold(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)

    return unique

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", required=True)
    parser.add_argument("--chain", required=True)
    parser.add_argument("--out", required=False)
    args = parser.parse_args()

    country_key = args.country.strip().lower()
    if country_key not in COUNTRY_TO_ISO:
        log(f"Unsupported country: {args.country}")
        log("Add the country to COUNTRY_TO_ISO in scripts/export_osm.py.")
        sys.exit(2)

    country_iso, country_name = COUNTRY_TO_ISO[country_key]
    chain = args.chain.strip()

    log(f"Exporting {chain} in {country_name}")

    all_rows = []
    total_elements = 0
    skipped = 0

    for mode in ["brand_shop", "name_shop", "operator_shop"]:
        log(f"\nMode: {mode}")
        query = build_query(country_iso, chain, mode)
        data = fetch_overpass(query)
        elements = data.get("elements", [])
        total_elements += len(elements)
        log(f"Found {len(elements)} OSM elements in mode {mode}.")

        mode_rows = []
        mode_skipped = 0

        for element in elements:
            row = element_to_row(element, country_name, chain)
            if row:
                mode_rows.append(row)
            else:
                mode_skipped += 1

        skipped += mode_skipped
        all_rows.extend(mode_rows)
        all_rows = dedupe(all_rows)

        log(f"Added {len(mode_rows)} rows from {mode}. Skipped without full address: {mode_skipped}. Total unique rows: {len(all_rows)}.")

    rows = dedupe(all_rows)

    if args.out:
        out_path = Path(args.out)
    else:
        out_path = Path("exports") / f"{safe_filename(country_name)}_{safe_filename(chain)}.csv"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "chain_requested",
        "name",
        "brand",
        "operator",
        "street",
        "housenumber",
        "postcode",
        "city",
        "country",
        "address_formatted",
        "osm_type",
        "osm_id",
        "source",
    ]

    with out_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    log("\nExport complete")
    log(f"Total OSM elements seen: {total_elements}")
    log(f"Rows with full formatted address: {len(rows)}")
    log(f"Skipped without full address: {skipped}")
    log(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
