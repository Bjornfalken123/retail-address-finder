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
    "ch": ("CH", "Switzerland"),
}

SEARCH_KEYS = ["name", "brand", "operator"]

SUBTYPE_SELECTORS = {
    "auto": [],
    "all": [],

    "supermarket": ['["shop"="supermarket"]'],
    "convenience": ['["shop"="convenience"]'],
    "fashion": ['["shop"="clothes"]', '["shop"="fashion"]', '["shop"="shoes"]'],
    "electronics": ['["shop"="electronics"]', '["shop"="mobile_phone"]', '["shop"="computer"]'],
    "furniture": ['["shop"="furniture"]', '["shop"="doityourself"]', '["shop"="garden_centre"]'],
    "general_shop": ['["shop"]'],

    "fast_food": ['["amenity"="fast_food"]'],
    "restaurant": ['["amenity"="restaurant"]'],
    "cafe": ['["amenity"="cafe"]'],
    "bar_pub": ['["amenity"="bar"]', '["amenity"="pub"]'],
    "food_court": ['["amenity"="food_court"]'],
    "ice_cream": ['["amenity"="ice_cream"]'],

    "fuel": ['["amenity"="fuel"]'],
    "charging": ['["amenity"="charging_station"]'],
    "car_rental": ['["amenity"="car_rental"]', '["amenity"="car_sharing"]'],
    "car_service": ['["shop"="car"]', '["shop"="car_repair"]', '["shop"="tyres"]'],
    "bike_rental": ['["amenity"="bicycle_rental"]'],

    "hotel": ['["tourism"="hotel"]'],
    "motel": ['["tourism"="motel"]'],
    "hostel": ['["tourism"="hostel"]'],
    "guest_house": ['["tourism"="guest_house"]'],

    "bank": ['["amenity"="bank"]', '["amenity"="atm"]'],
    "post_parcel": ['["amenity"="post_office"]', '["amenity"="parcel_locker"]'],
    "beauty": ['["shop"="hairdresser"]', '["shop"="beauty"]', '["shop"="cosmetics"]'],
    "optician": ['["shop"="optician"]'],

    "pharmacy": ['["amenity"="pharmacy"]', '["shop"="chemist"]'],
    "clinic": ['["amenity"="clinic"]'],
    "dentist": ['["amenity"="dentist"]'],
    "doctors": ['["amenity"="doctors"]'],
    "veterinary": ['["amenity"="veterinary"]'],

    "fitness": ['["leisure"="fitness_centre"]'],
    "sports": ['["leisure"="sports_centre"]'],
    "cinema": ['["amenity"="cinema"]', '["amenity"="theatre"]', '["leisure"="cinema"]'],
    "bowling": ['["leisure"="bowling_alley"]'],
    "arcade": ['["leisure"="amusement_arcade"]'],
}

CATEGORY_SELECTORS = {
    "all": [
        '["shop"]',
        '["amenity"="fast_food"]',
        '["amenity"="restaurant"]',
        '["amenity"="cafe"]',
        '["amenity"="bar"]',
        '["amenity"="pub"]',
        '["amenity"="ice_cream"]',
        '["amenity"="food_court"]',
        '["amenity"="pharmacy"]',
        '["amenity"="clinic"]',
        '["amenity"="dentist"]',
        '["amenity"="doctors"]',
        '["amenity"="veterinary"]',
        '["amenity"="fuel"]',
        '["amenity"="charging_station"]',
        '["amenity"="car_rental"]',
        '["amenity"="car_sharing"]',
        '["amenity"="bicycle_rental"]',
        '["amenity"="bank"]',
        '["amenity"="atm"]',
        '["amenity"="post_office"]',
        '["amenity"="parcel_locker"]',
        '["tourism"="hotel"]',
        '["tourism"="motel"]',
        '["tourism"="hostel"]',
        '["tourism"="guest_house"]',
        '["leisure"="fitness_centre"]',
        '["leisure"="sports_centre"]',
        '["leisure"="bowling_alley"]',
        '["leisure"="cinema"]',
        '["leisure"="amusement_arcade"]',
        '["amenity"="cinema"]',
        '["amenity"="theatre"]',
    ],
    "retail_grocery": [
        '["shop"="supermarket"]',
        '["shop"="convenience"]',
        '["shop"="greengrocer"]',
        '["shop"="department_store"]',
        '["shop"="mall"]',
        '["shop"="clothes"]',
        '["shop"="shoes"]',
        '["shop"="fashion"]',
        '["shop"="electronics"]',
        '["shop"="mobile_phone"]',
        '["shop"="computer"]',
        '["shop"="furniture"]',
        '["shop"="doityourself"]',
        '["shop"="garden_centre"]',
        '["shop"]',
    ],
    "food_restaurants": [
        '["amenity"="fast_food"]',
        '["amenity"="restaurant"]',
        '["amenity"="cafe"]',
        '["amenity"="bar"]',
        '["amenity"="pub"]',
        '["amenity"="ice_cream"]',
        '["amenity"="food_court"]',
    ],
    "mobility_fuel": [
        '["amenity"="fuel"]',
        '["amenity"="charging_station"]',
        '["amenity"="car_rental"]',
        '["amenity"="car_sharing"]',
        '["amenity"="bicycle_rental"]',
        '["shop"="car"]',
        '["shop"="car_repair"]',
        '["shop"="tyres"]',
    ],
    "hotels": [
        '["tourism"="hotel"]',
        '["tourism"="motel"]',
        '["tourism"="hostel"]',
        '["tourism"="guest_house"]',
        '["tourism"="apartment"]',
    ],
    "services": [
        '["amenity"="bank"]',
        '["amenity"="atm"]',
        '["amenity"="post_office"]',
        '["amenity"="parcel_locker"]',
        '["shop"="hairdresser"]',
        '["shop"="beauty"]',
        '["shop"="cosmetics"]',
        '["shop"="optician"]',
    ],
    "healthcare_pharmacy": [
        '["amenity"="pharmacy"]',
        '["amenity"="clinic"]',
        '["amenity"="dentist"]',
        '["amenity"="doctors"]',
        '["amenity"="veterinary"]',
        '["shop"="chemist"]',
        '["shop"="optician"]',
    ],
    "fitness_entertainment": [
        '["leisure"="fitness_centre"]',
        '["leisure"="sports_centre"]',
        '["leisure"="bowling_alley"]',
        '["leisure"="cinema"]',
        '["leisure"="amusement_arcade"]',
        '["amenity"="cinema"]',
        '["amenity"="theatre"]',
    ],
}

KNOWN_CHAIN_ALIASES = {
    "max": ["MAX", "Max", "MAX Burgers", "Max Hamburgare"],
    "max hamburgare": ["MAX", "Max", "MAX Burgers", "Max Hamburgare"],
    "max burgers": ["MAX", "Max", "MAX Burgers", "Max Hamburgare"],
    "mcdonalds": ["McDonald's", "McDonalds", "McDonald’s"],
    "mcdonald's": ["McDonald's", "McDonalds", "McDonald’s"],
    "burger king": ["Burger King"],
    "kfc": ["KFC"],
    "subway": ["Subway"],
    "pizza hut": ["Pizza Hut"],
    "dominos": ["Domino's", "Dominos", "Domino’s Pizza"],
    "starbucks": ["Starbucks"],
    "espresso house": ["Espresso House"],
    "joe & the juice": ["Joe & The Juice", "JOE & THE JUICE"],

    "kiwi": ["Kiwi", "KIWI"],
    "rema 1000": ["REMA 1000", "Rema 1000"],
    "lidl": ["Lidl", "LIDL"],
    "aldi": ["Aldi", "ALDI"],
    "carrefour": ["Carrefour"],
    "albert heijn": ["Albert Heijn"],
    "tesco": ["Tesco"],
    "ica": ["ICA"],
    "coop": ["Coop", "COOP"],
    "7-eleven": ["7-Eleven", "Seven Eleven"],

    "circle k": ["Circle K"],
    "shell": ["Shell"],
    "bp": ["BP"],
    "esso": ["Esso"],
    "okq8": ["OKQ8"],
    "preem": ["Preem"],

    "ikea": ["IKEA", "Ikea"],
    "h&m": ["H&M", "Hennes & Mauritz"],
    "hm": ["H&M", "Hennes & Mauritz"],
    "zara": ["Zara"],
    "elgiganten": ["Elgiganten"],

    "sats": ["SATS", "Sats"],
    "fitness24seven": ["Fitness24Seven", "Fitness 24 Seven"],
    "nordic wellness": ["Nordic Wellness"],
    "basic-fit": ["Basic-Fit", "Basic Fit"],

    "scandic": ["Scandic"],
    "radisson": ["Radisson"],
    "best western": ["Best Western"],
    "marriott": ["Marriott"],
    "hilton": ["Hilton"],

    "boots": ["Boots"],
    "apoteket": ["Apoteket"],
    "lloydsapotek": ["LloydsApotek", "Lloyds Apotek"],
    "walgreens": ["Walgreens"],

    "dhl": ["DHL"],
    "ups": ["UPS"],
    "fedex": ["FedEx"],
    "postnord": ["PostNord"],
    "instabox": ["Instabox"],

    "nordea": ["Nordea"],
    "seb": ["SEB"],
    "swedbank": ["Swedbank"],
    "handelsbanken": ["Handelsbanken"],
}

KNOWN_CHAIN_SELECTORS = {
    "max": ("food_restaurants", ['["amenity"="fast_food"]']),
    "max hamburgare": ("food_restaurants", ['["amenity"="fast_food"]']),
    "max burgers": ("food_restaurants", ['["amenity"="fast_food"]']),
    "mcdonalds": ("food_restaurants", ['["amenity"="fast_food"]']),
    "mcdonald's": ("food_restaurants", ['["amenity"="fast_food"]']),
    "burger king": ("food_restaurants", ['["amenity"="fast_food"]']),
    "kfc": ("food_restaurants", ['["amenity"="fast_food"]']),
    "subway": ("food_restaurants", ['["amenity"="fast_food"]']),
    "starbucks": ("food_restaurants", ['["amenity"="cafe"]']),
    "espresso house": ("food_restaurants", ['["amenity"="cafe"]']),

    "kiwi": ("retail_grocery", ['["shop"="supermarket"]']),
    "rema 1000": ("retail_grocery", ['["shop"="supermarket"]']),
    "lidl": ("retail_grocery", ['["shop"="supermarket"]']),
    "aldi": ("retail_grocery", ['["shop"="supermarket"]']),
    "carrefour": ("retail_grocery", ['["shop"="supermarket"]', '["shop"="convenience"]']),
    "albert heijn": ("retail_grocery", ['["shop"="supermarket"]']),
    "ica": ("retail_grocery", ['["shop"="supermarket"]']),
    "coop": ("retail_grocery", ['["shop"="supermarket"]', '["shop"="convenience"]']),
    "7-eleven": ("retail_grocery", ['["shop"="convenience"]']),

    "circle k": ("mobility_fuel", ['["amenity"="fuel"]']),
    "shell": ("mobility_fuel", ['["amenity"="fuel"]']),
    "bp": ("mobility_fuel", ['["amenity"="fuel"]']),
    "esso": ("mobility_fuel", ['["amenity"="fuel"]']),
    "okq8": ("mobility_fuel", ['["amenity"="fuel"]']),
    "preem": ("mobility_fuel", ['["amenity"="fuel"]']),

    "ikea": ("retail_grocery", ['["shop"="furniture"]']),
    "h&m": ("retail_grocery", ['["shop"="clothes"]', '["shop"="fashion"]']),
    "hm": ("retail_grocery", ['["shop"="clothes"]', '["shop"="fashion"]']),
    "zara": ("retail_grocery", ['["shop"="clothes"]', '["shop"="fashion"]']),
    "elgiganten": ("retail_grocery", ['["shop"="electronics"]']),

    "sats": ("fitness_entertainment", ['["leisure"="fitness_centre"]']),
    "fitness24seven": ("fitness_entertainment", ['["leisure"="fitness_centre"]']),
    "nordic wellness": ("fitness_entertainment", ['["leisure"="fitness_centre"]']),
    "basic-fit": ("fitness_entertainment", ['["leisure"="fitness_centre"]']),

    "scandic": ("hotels", ['["tourism"="hotel"]']),
    "radisson": ("hotels", ['["tourism"="hotel"]']),
    "best western": ("hotels", ['["tourism"="hotel"]']),
    "marriott": ("hotels", ['["tourism"="hotel"]']),
    "hilton": ("hotels", ['["tourism"="hotel"]']),

    "boots": ("healthcare_pharmacy", ['["amenity"="pharmacy"]', '["shop"="chemist"]']),
    "apoteket": ("healthcare_pharmacy", ['["amenity"="pharmacy"]']),
    "lloydsapotek": ("healthcare_pharmacy", ['["amenity"="pharmacy"]']),
    "walgreens": ("healthcare_pharmacy", ['["amenity"="pharmacy"]']),

    "dhl": ("services", ['["amenity"="post_office"]', '["amenity"="parcel_locker"]']),
    "ups": ("services", ['["amenity"="post_office"]', '["amenity"="parcel_locker"]']),
    "fedex": ("services", ['["amenity"="post_office"]']),
    "postnord": ("services", ['["amenity"="post_office"]', '["amenity"="parcel_locker"]']),
    "instabox": ("services", ['["amenity"="parcel_locker"]']),

    "nordea": ("services", ['["amenity"="bank"]', '["amenity"="atm"]']),
    "seb": ("services", ['["amenity"="bank"]', '["amenity"="atm"]']),
    "swedbank": ("services", ['["amenity"="bank"]', '["amenity"="atm"]']),
    "handelsbanken": ("services", ['["amenity"="bank"]', '["amenity"="atm"]']),
}

SMART_RULES = [
    ("food_restaurants", ["max", "burger", "hamburg", "mcdonald", "kfc", "subway", "pizza", "chicken", "kebab"], ['["amenity"="fast_food"]']),
    ("food_restaurants", ["coffee", "espresso", "cafe", "café", "juice"], ['["amenity"="cafe"]']),
    ("retail_grocery", ["supermarket", "grocery", "lidl", "aldi", "kiwi", "rema", "carrefour", "tesco", "ica", "coop"], ['["shop"="supermarket"]']),
    ("retail_grocery", ["fashion", "clothes", "zara", "h&m", "hm"], ['["shop"="clothes"]', '["shop"="fashion"]']),
    ("retail_grocery", ["electronics", "phone", "mobile", "elgiganten"], ['["shop"="electronics"]']),
    ("retail_grocery", ["ikea", "furniture"], ['["shop"="furniture"]']),
    ("mobility_fuel", ["fuel", "gas", "petrol", "shell", "circle k", "esso", "bp", "okq8", "preem"], ['["amenity"="fuel"]']),
    ("mobility_fuel", ["charge", "charging", "supercharger", "ionity", "tesla"], ['["amenity"="charging_station"]']),
    ("hotels", ["hotel", "scandic", "radisson", "hilton", "marriott", "inn", "motel", "hostel"], ['["tourism"="hotel"]']),
    ("services", ["bank", "nordea", "seb", "swedbank", "handelsbanken"], ['["amenity"="bank"]', '["amenity"="atm"]']),
    ("services", ["post", "dhl", "ups", "fedex", "parcel", "locker", "instabox", "postnord"], ['["amenity"="post_office"]', '["amenity"="parcel_locker"]']),
    ("healthcare_pharmacy", ["pharmacy", "apotek", "chemist", "boots", "walgreens"], ['["amenity"="pharmacy"]', '["shop"="chemist"]']),
    ("fitness_entertainment", ["fitness", "gym", "sats", "wellness", "basic-fit"], ['["leisure"="fitness_centre"]']),
    ("fitness_entertainment", ["cinema", "movie", "film", "theatre", "bowling"], ['["amenity"="cinema"]', '["amenity"="theatre"]', '["leisure"="bowling_alley"]']),
]


def log(message: str) -> None:
    print(message, flush=True)


def normalize_chain(chain: str) -> str:
    return chain.strip().lower().replace("’", "'")


def get_chain_aliases(chain: str) -> list[str]:
    normalized = normalize_chain(chain)
    return KNOWN_CHAIN_ALIASES.get(normalized, [chain.strip()])


def overpass_regex_for_chain(chain: str) -> str:
    aliases = get_chain_aliases(chain)
    escaped_aliases = []

    for alias in aliases:
        escaped = re.sub(r"([.^$*+?{}\[\]\\|()])", r"\\\1", alias.strip())
        escaped = re.sub(r"\s+", " ", escaped)
        escaped_aliases.append(escaped)

    return "|".join(escaped_aliases)


def get_selectors_for_category_and_subtype(category: str, subtype: str) -> list[str]:
    if subtype not in {"auto", "all"} and subtype in SUBTYPE_SELECTORS:
        return SUBTYPE_SELECTORS[subtype]

    return CATEGORY_SELECTORS.get(category, CATEGORY_SELECTORS["all"])


def infer_smart_selectors(chain: str, category: str, subtype: str) -> list[str]:
    if subtype not in {"auto", "all"}:
        return get_selectors_for_category_and_subtype(category, subtype)

    normalized = normalize_chain(chain)

    if normalized in KNOWN_CHAIN_SELECTORS:
        known_category, selectors = KNOWN_CHAIN_SELECTORS[normalized]
        if category == "all" or category == known_category:
            return selectors

    for rule_category, tokens, selectors in SMART_RULES:
        if category != "all" and category != rule_category:
            continue

        if any(token in normalized for token in tokens):
            return selectors

    return get_selectors_for_category_and_subtype(category, subtype)


def build_chain_query(country_iso: str, chain: str, search_key: str, selector: str) -> str:
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


def build_category_query(country_iso: str, selector: str) -> str:
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
                        "User-Agent": "RetailAddressFinder/0.6 Category Exports (GitHub Actions)",
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
                time.sleep(5 * attempt)

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

    return "" if lat is None else str(lat), "" if lon is None else str(lon)


def detect_category(tags: dict) -> str:
    shop = get_tag(tags, "shop")
    amenity = get_tag(tags, "amenity")
    tourism = get_tag(tags, "tourism")
    leisure = get_tag(tags, "leisure")

    if shop:
        if shop in {"supermarket", "convenience", "greengrocer"}:
            return "Grocery / convenience"
        if shop in {"clothes", "shoes", "fashion"}:
            return "Fashion retail"
        if shop in {"electronics", "mobile_phone", "computer"}:
            return "Electronics retail"
        if shop in {"furniture", "doityourself", "garden_centre"}:
            return "Home / furniture retail"
        if shop in {"hairdresser", "beauty", "cosmetics"}:
            return "Beauty / wellness"
        if shop in {"chemist", "optician"}:
            return "Healthcare / pharmacy"
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

    street_line = f"{street} {housenumber}".strip() if street or housenumber else ""
    parts = [street_line, postcode, city, country_name]
    usable_parts = [p for p in parts if p]

    if len(usable_parts) > 1:
        return " ".join(usable_parts), "usable"

    return "", "coordinates_only"


def element_to_row(element: dict, country_name: str, chain_requested: str, export_mode: str, requested_category: str, requested_subtype: str) -> dict:
    tags = element.get("tags", {}) or {}
    lat, lon = get_lat_lon(element)
    address_formatted, address_quality = build_formatted_address(tags, country_name)

    if not address_formatted:
        address_formatted = f"{lat},{lon}" if lat and lon else ""

    return {
        "export_mode": export_mode,
        "chain_requested": chain_requested,
        "requested_category": requested_category,
        "requested_subtype": requested_subtype,
        "name": get_tag(tags, "name"),
        "brand": get_tag(tags, "brand"),
        "operator": get_tag(tags, "operator"),
        "category": detect_category(tags),
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


def run_chain_queries(country_iso, country_name, chain, selectors, export_mode, category, subtype, phase_name):
    rows = []
    total_elements = 0
    failed_queries = []
    total_queries = len(SEARCH_KEYS) * len(selectors)
    query_no = 0

    log(f"\nStarting query phase: {phase_name}")
    log(f"Selectors in this phase: {len(selectors)}")
    log(f"Total queries in this phase: {total_queries}")

    for search_key in SEARCH_KEYS:
        for selector in selectors:
            query_no += 1
            label = f"{phase_name}: {search_key} {selector}"
            log(f"\n[{query_no}/{total_queries}] Query: {label}")

            query = build_chain_query(country_iso, chain, search_key, selector)

            try:
                data = fetch_overpass(query)
            except Exception as exc:
                failed_queries.append(f"{label}: {type(exc).__name__}: {exc}")
                log(f"Skipping failed query: {label}")
                continue

            elements = data.get("elements", [])
            total_elements += len(elements)
            log(f"Found {len(elements)} OSM elements.")

            new_rows = [
                element_to_row(element, country_name, chain, export_mode, category, subtype)
                for element in elements
            ]

            rows.extend(new_rows)
            rows = dedupe(rows)
            log(f"Unique rows in phase: {len(rows)}")
            time.sleep(0.4)

    return rows, total_elements, failed_queries


def run_category_queries(country_iso, country_name, selectors, export_mode, category, subtype):
    rows = []
    total_elements = 0
    failed_queries = []
    total_queries = len(selectors)

    log("\nStarting category export")
    log(f"Selectors: {len(selectors)}")
    log(f"Total queries: {total_queries}")

    for index, selector in enumerate(selectors, start=1):
        label = f"category: {selector}"
        log(f"\n[{index}/{total_queries}] Query: {label}")

        query = build_category_query(country_iso, selector)

        try:
            data = fetch_overpass(query)
        except Exception as exc:
            failed_queries.append(f"{label}: {type(exc).__name__}: {exc}")
            log(f"Skipping failed query: {label}")
            continue

        elements = data.get("elements", [])
        total_elements += len(elements)
        log(f"Found {len(elements)} OSM elements.")

        new_rows = [
            element_to_row(element, country_name, "", export_mode, category, subtype)
            for element in elements
        ]

        rows.extend(new_rows)
        rows = dedupe(rows)
        log(f"Unique rows so far: {len(rows)}")
        time.sleep(0.4)

    return rows, total_elements, failed_queries


def write_csv(rows: list[dict], out_path: Path) -> None:
    fields = [
        "export_mode",
        "chain_requested",
        "requested_category",
        "requested_subtype",
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

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-mode", required=False, default="chain")
    parser.add_argument("--country", required=True)
    parser.add_argument("--chain", required=False, default="")
    parser.add_argument("--category", required=False, default="all")
    parser.add_argument("--subtype", required=False, default="auto")
    parser.add_argument("--out", required=False)
    args = parser.parse_args()

    export_mode = args.export_mode.strip().lower()
    country_key = args.country.strip().lower()
    chain = args.chain.strip()
    category = args.category.strip().lower()
    subtype = args.subtype.strip().lower()

    if export_mode not in {"chain", "category"}:
        log(f"Invalid export mode: {export_mode}")
        sys.exit(2)

    if country_key not in COUNTRY_TO_ISO:
        log(f"Unsupported country: {args.country}")
        log("Add the country to COUNTRY_TO_ISO in scripts/export_osm.py.")
        sys.exit(2)

    if category not in CATEGORY_SELECTORS:
        log(f"Unknown category '{category}', falling back to all.")
        category = "all"

    if export_mode == "chain" and not chain:
        log("Chain is required when export mode is 'chain'.")
        sys.exit(2)

    country_iso, country_name = COUNTRY_TO_ISO[country_key]

    log(f"Export mode: {export_mode}")
    log(f"Country: {country_name}")
    log(f"Category: {category}")
    log(f"Subtype: {subtype}")

    rows = []
    total_elements = 0
    failed_queries = []

    if export_mode == "category":
        selectors = get_selectors_for_category_and_subtype(category, subtype)

        if subtype == "auto":
            selectors = CATEGORY_SELECTORS[category]

        rows, total_elements, failed_queries = run_category_queries(
            country_iso=country_iso,
            country_name=country_name,
            selectors=selectors,
            export_mode=export_mode,
            category=category,
            subtype=subtype,
        )

    else:
        log(f"Chain: {chain}")
        log(f"Aliases: {', '.join(get_chain_aliases(chain))}")

        smart_selectors = infer_smart_selectors(chain, category, subtype)
        fallback_selectors = get_selectors_for_category_and_subtype(category, subtype)

        if subtype == "auto":
            fallback_selectors = CATEGORY_SELECTORS[category]

        rows_smart, elements_smart, failures_smart = run_chain_queries(
            country_iso=country_iso,
            country_name=country_name,
            chain=chain,
            selectors=smart_selectors,
            export_mode=export_mode,
            category=category,
            subtype=subtype,
            phase_name="smart",
        )

        rows.extend(rows_smart)
        rows = dedupe(rows)
        total_elements += elements_smart
        failed_queries.extend(failures_smart)

        fallback_needed = len(rows) < 3 and fallback_selectors != smart_selectors

        if fallback_needed:
            log("\nSmart query returned fewer than 3 unique rows. Expanding within the selected category/subtype.")
            remaining_selectors = [selector for selector in fallback_selectors if selector not in smart_selectors]

            rows_fallback, elements_fallback, failures_fallback = run_chain_queries(
                country_iso=country_iso,
                country_name=country_name,
                chain=chain,
                selectors=remaining_selectors,
                export_mode=export_mode,
                category=category,
                subtype=subtype,
                phase_name="fallback",
            )

            rows.extend(rows_fallback)
            rows = dedupe(rows)
            total_elements += elements_fallback
            failed_queries.extend(failures_fallback)

    if args.out:
        out_path = Path(args.out)
    else:
        name = f"{country_name}_{chain or category}_{subtype}".replace(" ", "_")
        out_path = Path("exports") / f"{name}.csv"

    write_csv(rows, out_path)

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
