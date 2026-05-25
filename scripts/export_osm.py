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
    "sweden": ("SE", "Sweden"),
    "sverige": ("SE", "Sweden"),
    "denmark": ("DK", "Denmark"),
    "danmark": ("DK", "Denmark"),
    "finland": ("FI", "Finland"),
    "france": ("FR", "France"),
    "frankrike": ("FR", "France"),
    "belgium": ("BE", "Belgium"),
    "belgien": ("BE", "Belgium"),
    "netherlands": ("NL", "Netherlands"),
    "nederländerna": ("NL", "Netherlands"),
    "nederlanderna": ("NL", "Netherlands"),
    "germany": ("DE", "Germany"),
    "tyskland": ("DE", "Germany"),
    "spain": ("ES", "Spain"),
    "spanien": ("ES", "Spain"),
    "italy": ("IT", "Italy"),
    "italien": ("IT", "Italy"),
    "usa": ("US", "USA"),
    "united states": ("US", "USA"),
    "united states of america": ("US", "USA"),
    "united kingdom": ("GB", "United Kingdom"),
    "uk": ("GB", "United Kingdom"),
    "great britain": ("GB", "United Kingdom"),
    "ireland": ("IE", "Ireland"),
    "poland": ("PL", "Poland"),
    "portugal": ("PT", "Portugal"),
    "austria": ("AT", "Austria"),
    "switzerland": ("CH", "Switzerland"),
}

# Broad B2C category selectors. We intentionally avoid pure office/company/building-only
# matches so the output focuses on consumer-facing physical locations.
B2C_SELECTORS = [
    # Retail
    '["shop"]',
    # Food & restaurants
    '["amenity"~"fast_food|restaurant|cafe|bar|pub|ice_cream|food_court"]',
    # Pharmacy / healthcare
    '["amenity"~"pharmacy|clinic|dentist|doctors|veterinary"]',
    # Fuel / mobility / transport service
    '["amenity"~"fuel|car_rental|car_sharing|bicycle_rental|charging_station"]',
    # Finance / postal / parcel
    '["amenity"~"bank|atm|post_office|parcel_locker"]',
    # Hotels / accommodation
    '["tourism"~"hotel|motel|hostel|guest_house|apartment"]',
    # Fitness / entertainment
    '["leisure"~"fitness_centre|sports_centre|bowling_alley|cinema|amusement_arcade"]',
    # Some cinemas are tagged as amenity
    '["amenity"~"cinema|theatre"]',
    # Education / childcare chains, if relevant
    '["amenity"~"school|kindergarten|college|university"]',
]
CATEGORY_SELECTORS = {
    "all": B2C_SELECTORS,

    "retail_grocery": [
        '["shop"]',
    ],

    "food_restaurants": [
        '["amenity"~"fast_food|restaurant|cafe|bar|pub|ice_cream|food_court"]',
    ],

    "mobility_fuel": [
        '["amenity"~"fuel|car_rental|car_sharing|bicycle_rental|charging_station"]',
        '["shop"~"car|car_repair|tyres"]',
    ],

    "hotels": [
        '["tourism"~"hotel|motel|hostel|guest_house|apartment"]',
    ],

    "services": [
        '["amenity"~"bank|atm|post_office|parcel_locker"]',
        '["shop"~"hairdresser|beauty|cosmetics|optician"]',
    ],

    "healthcare_pharmacy": [
        '["amenity"~"pharmacy|clinic|dentist|doctors|veterinary"]',
        '["shop"~"chemist|optician"]',
    ],

    "fitness_entertainment": [
        '["leisure"~"fitness_centre|sports_centre|bowling_alley|cinema|amusement_arcade"]',
        '["amenity"~"cinema|theatre"]',
    ],
}

SEARCH_KEYS = ["brand", "name", "operator"]


def log(message: str) -> None:
    print(message, flush=True)


def safe_filename(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9åäöæøéüß]+", "_", value, flags=re.I)
    return value.strip("_") or "export"


def overpass_regex_for_chain(chain: str) -> str:
    """
    Escape regex special characters but do not escape spaces.
    This avoids some Overpass 406 errors for names like 'REMA 1000'.
    """
    chain = chain.strip()
    escaped = re.sub(r"([.^$*+?{}\[\]\\|()])", r"\\\1", chain)
    escaped = re.sub(r"\s+", " ", escaped)
    return escaped


def build_query(country_iso: str, chain: str, search_key: str, selector: str) -> str:
    chain_regex = overpass_regex_for_chain(chain)

    return f"""
[out:json][timeout:120];
area["ISO3166-1"="{country_iso}"][admin_level=2]->.searchArea;
(
  node{selector}["{search_key}"~"{chain_regex}",i](area.searchArea);
  way{selector}["{search_key}"~"{chain_regex}",i](area.searchArea);
  relation{selector}["{search_key}"~"{chain_regex}",i](area.searchArea);
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
                        "User-Agent": "RetailAddressFinder/0.3 B2C (GitHub Actions)",
                        "Accept": "application/json",
                    },
                )

                if response.status_code == 406:
                    preview = response.text[:600].replace("\n", " ")
                    raise RuntimeError(
                        f"Overpass rejected query with 406. Response preview: {preview}"
                    )

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


def get_lat_lon(element: dict) -> tuple[str, str]:
    lat = element.get("lat")
    lon = element.get("lon")

    center = element.get("center") or {}

    if lat is None:
        lat = center.get("lat")
    if lon is None:
        lon = center.get("lon")

    return (
        "" if lat is None else str(lat),
        "" if lon is None else str(lon),
    )


def detect_category(tags: dict) -> str:
    shop = get_tag(tags, "shop")
    amenity = get_tag(tags, "amenity")
    tourism = get_tag(tags, "tourism")
    leisure = get_tag(tags, "leisure")

    if shop:
        if shop in {"supermarket", "convenience", "greengrocer"}:
            return "Grocery / convenience"
        if shop in {"chemist"}:
            return "Pharmacy / chemist"
        if shop in {"clothes", "shoes", "fashion", "jewelry"}:
            return "Fashion retail"
        if shop in {"electronics", "mobile_phone", "computer"}:
            return "Electronics retail"
        if shop in {"furniture", "doityourself", "garden_centre"}:
            return "Home / furniture retail"
        if shop in {"hairdresser", "beauty", "cosmetics"}:
            return "Beauty / wellness"
        if shop in {"car", "car_repair", "tyres"}:
            return "Automotive retail/service"
        return f"Retail: {shop}"

    if amenity:
        if amenity in {"fast_food", "restaurant", "cafe", "bar", "pub", "ice_cream", "food_court"}:
            return "Food & restaurants"
        if amenity in {"pharmacy", "clinic", "dentist", "doctors", "veterinary"}:
            return "Healthcare / pharmacy"
        if amenity in {"fuel", "charging_station"}:
            return "Fuel / charging"
        if amenity in {"bank", "atm"}:
            return "Banking"
        if amenity in {"post_office", "parcel_locker"}:
            return "Post / parcel"
        if amenity in {"car_rental", "car_sharing", "bicycle_rental"}:
            return "Mobility / rental"
        if amenity in {"cinema", "theatre"}:
            return "Entertainment"
        if amenity in {"school", "kindergarten", "college", "university"}:
            return "Education"
        return f"Service: {amenity}"

    if tourism:
        if tourism in {"hotel", "motel", "hostel", "guest_house", "apartment"}:
            return "Hotel / accommodation"
        return f"Tourism: {tourism}"

    if leisure:
        if leisure in {"fitness_centre", "sports_centre"}:
            return "Fitness / sports"
        if leisure in {"bowling_alley", "cinema", "amusement_arcade"}:
            return "Entertainment"
        return f"Leisure: {leisure}"

    return "Other B2C"


def build_formatted_address(tags: dict, country_name: str) -> tuple[str, str]:
    """
    Returns (address_formatted, address_quality)

    strict: street + house number + postcode + city + country
    usable: some useful address fields exist, but not all
    coordinates_only: no usable address fields; use lat/lon columns
    """
    street = get_tag(tags, "addr:street")
    housenumber = get_tag(tags, "addr:housenumber")
    postcode = get_tag(tags, "addr:postcode")
    city = get_tag(tags, "addr:city", "addr:town", "addr:village", "addr:municipality")
    full = get_tag(tags, "addr:full")

    if street and housenumber and postcode and city:
        return f"{street} {housenumber} {postcode} {city} {country_name}", "strict"

    if full:
        parts = [full, postcode, city, country_name]
        return " ".join([p for p in parts if p]), "usable"

    street_line = ""
    if street and housenumber:
        street_line = f"{street} {housenumber}"
    elif street:
        street_line = street
    elif housenumber:
        street_line = housenumber

    parts = [street_line, postcode, city, country_name]
    usable_parts = [p for p in parts if p]

    if len(usable_parts) > 1:
        return " ".join(usable_parts), "usable"

    return "", "coordinates_only"


def element_to_row(element: dict, country_name: str, chain: str) -> dict:
    tags = element.get("tags", {}) or {}

    lat, lon = get_lat_lon(element)
    address_formatted, address_quality = build_formatted_address(tags, country_name)

    if not address_formatted:
        address_formatted = f"{lat},{lon}" if lat and lon else ""

    category = detect_category(tags)

    return {
        "chain_requested": chain,
        "name": get_tag(tags, "name"),
        "brand": get_tag(tags, "brand"),
        "operator": get_tag(tags, "operator"),
        "category": category,
        "shop": get_tag(tags, "shop"),
        "amenity": get_tag(tags, "amenity"),
        "tourism": get_tag(tags, "tourism"),
        "leisure": get_tag(tags, "leisure"),
        "street": get_tag(tags, "addr:street"),
        "housenumber": get_tag(tags, "addr:housenumber"),
        "postcode": get_tag(tags, "addr:postcode"),
        "city": get_tag(tags, "addr:city", "addr:town", "addr:village", "addr:municipality"),
        "country": country_name,
        "address_formatted": address_formatted,
        "address_quality": address_quality,
        "latitude": lat,
        "longitude": lon,
        "osm_type": element.get("type", ""),
        "osm_id": element.get("id", ""),
        "source": "OpenStreetMap via Overpass API",
    }


def dedupe(rows: list[dict]) -> list[dict]:
    seen = set()
    unique = []

    for row in rows:
        if row.get("osm_type") and row.get("osm_id"):
            key = (row["osm_type"], str(row["osm_id"]))
        else:
            key = (
                row.get("address_formatted", "").casefold(),
                row.get("latitude", ""),
                row.get("longitude", ""),
                row.get("name", "").casefold(),
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
    parser.add_argument("--category", required=False, default="all")
    parser.add_argument("--out", required=False)
    args = parser.parse_args()

    country_key = args.country.strip().lower()

    if country_key not in COUNTRY_TO_ISO:
        log(f"Unsupported country: {args.country}")
        log("Add the country to COUNTRY_TO_ISO in scripts/export_osm.py.")
        sys.exit(2)

    country_iso, country_name = COUNTRY_TO_ISO[country_key]
    chain = args.chain.strip()
    category = args.category.strip().lower()

    if category not in CATEGORY_SELECTORS:
        log(f"Unknown category '{category}', falling back to all B2C locations.")
        category = "all"

    selected_selectors = CATEGORY_SELECTORS[category]

    log(f"Exporting B2C locations for '{chain}' in {country_name}, category={category}")

    all_rows = []
    total_elements = 0
    failed_queries = []

    total_queries = len(SEARCH_KEYS) * len(selected_selectors)
    query_no = 0

    for search_key in SEARCH_KEYS:
        for selector in selected_selectors:
            query_no += 1
            label = f"{search_key} {selector}"
            log(f"\n[{query_no}/{total_queries}] Query: {label}")

            query = build_query(country_iso, chain, search_key, selector)

            try:
                data = fetch_overpass(query)
            except Exception as exc:
                failed_queries.append(f"{label}: {type(exc).__name__}: {exc}")
                log(f"Skipping failed query: {label}")
                continue

            elements = data.get("elements", [])
            total_elements += len(elements)
            log(f"Found {len(elements)} OSM elements.")

            mode_rows = [element_to_row(element, country_name, chain) for element in elements]
            all_rows.extend(mode_rows)
            all_rows = dedupe(all_rows)

            strict_count = sum(1 for r in mode_rows if r["address_quality"] == "strict")
            usable_count = sum(1 for r in mode_rows if r["address_quality"] == "usable")
            coord_count = sum(1 for r in mode_rows if r["address_quality"] == "coordinates_only")

            log(
                f"Added {len(mode_rows)} rows. "
                f"Strict: {strict_count}. "
                f"Usable: {usable_count}. "
                f"Coordinates only: {coord_count}. "
                f"Total unique rows: {len(all_rows)}."
            )

            time.sleep(1)

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
        "category",
        "shop",
        "amenity",
        "tourism",
        "leisure",
        "street",
        "housenumber",
        "postcode",
        "city",
        "country",
        "address_formatted",
        "address_quality",
        "latitude",
        "longitude",
        "osm_type",
        "osm_id",
        "source",
    ]

    with out_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    strict_total = sum(1 for r in rows if r["address_quality"] == "strict")
    usable_total = sum(1 for r in rows if r["address_quality"] == "usable")
    coord_total = sum(1 for r in rows if r["address_quality"] == "coordinates_only")

    log("\nExport complete")
    log(f"Total OSM elements seen before dedupe: {total_elements}")
    log(f"Unique rows written: {len(rows)}")
    log(f"Strict full addresses: {strict_total}")
    log(f"Usable partial addresses: {usable_total}")
    log(f"Coordinates only: {coord_total}")

    if failed_queries:
        log("\nFailed queries:")
        for failure in failed_queries:
            log(f"- {failure}")

    log(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
