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

B2C_SELECTORS = [
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
    '["tourism"="apartment"]',
    '["leisure"="fitness_centre"]',
    '["leisure"="sports_centre"]',
    '["leisure"="bowling_alley"]',
    '["leisure"="cinema"]',
    '["leisure"="amusement_arcade"]',
    '["amenity"="cinema"]',
    '["amenity"="theatre"]',
    '["amenity"="school"]',
    '["amenity"="kindergarten"]',
]

CATEGORY_SELECTORS = {
    "all": B2C_SELECTORS,

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
    "taco bell": ["Taco Bell"],
    "pizza hut": ["Pizza Hut"],
    "dominos": ["Domino's", "Dominos", "Domino’s Pizza"],
    "domino's": ["Domino's", "Dominos", "Domino’s Pizza"],

    "starbucks": ["Starbucks"],
    "espresso house": ["Espresso House"],
    "costa coffee": ["Costa Coffee"],
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
    "netto": ["Netto"],
    "spar": ["SPAR", "Spar"],
    "7-eleven": ["7-Eleven", "Seven Eleven"],
    "seven eleven": ["7-Eleven", "Seven Eleven"],

    "circle k": ["Circle K"],
    "shell": ["Shell"],
    "bp": ["BP"],
    "esso": ["Esso"],
    "totalenergies": ["TotalEnergies", "Total"],
    "total": ["TotalEnergies", "Total"],
    "okq8": ["OKQ8"],
    "preem": ["Preem"],

    "ikea": ["IKEA", "Ikea"],
    "hm": ["H&M", "Hennes & Mauritz"],
    "h&m": ["H&M", "Hennes & Mauritz"],
    "zara": ["Zara"],
    "elgiganten": ["Elgiganten"],
    "media markt": ["MediaMarkt", "Media Markt"],
    "mediamarkt": ["MediaMarkt", "Media Markt"],

    "sats": ["SATS", "Sats"],
    "fitness24seven": ["Fitness24Seven", "Fitness 24 Seven"],
    "fitness 24 seven": ["Fitness24Seven", "Fitness 24 Seven"],
    "nordic wellness": ["Nordic Wellness"],
    "basic-fit": ["Basic-Fit", "Basic Fit"],
    "basic fit": ["Basic-Fit", "Basic Fit"],

    "scandic": ["Scandic"],
    "radisson": ["Radisson"],
    "best western": ["Best Western"],
    "marriott": ["Marriott"],
    "hilton": ["Hilton"],

    "boots": ["Boots"],
    "apoteket": ["Apoteket"],
    "lloydsapotek": ["LloydsApotek", "Lloyds Apotek"],
    "lloyds apotek": ["LloydsApotek", "Lloyds Apotek"],
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
    "max": {
        "category": "food_restaurants",
        "selectors": ['["amenity"="fast_food"]'],
    },
    "max hamburgare": {
        "category": "food_restaurants",
        "selectors": ['["amenity"="fast_food"]'],
    },
    "max burgers": {
        "category": "food_restaurants",
        "selectors": ['["amenity"="fast_food"]'],
    },
    "mcdonalds": {
        "category": "food_restaurants",
        "selectors": ['["amenity"="fast_food"]'],
    },
    "mcdonald's": {
        "category": "food_restaurants",
        "selectors": ['["amenity"="fast_food"]'],
    },
    "burger king": {
        "category": "food_restaurants",
        "selectors": ['["amenity"="fast_food"]'],
    },
    "kfc": {
        "category": "food_restaurants",
        "selectors": ['["amenity"="fast_food"]'],
    },
    "subway": {
        "category": "food_restaurants",
        "selectors": ['["amenity"="fast_food"]'],
    },
    "pizza hut": {
        "category": "food_restaurants",
        "selectors": ['["amenity"="fast_food"]', '["amenity"="restaurant"]'],
    },
    "dominos": {
        "category": "food_restaurants",
        "selectors": ['["amenity"="fast_food"]', '["amenity"="restaurant"]'],
    },
    "domino's": {
        "category": "food_restaurants",
        "selectors": ['["amenity"="fast_food"]', '["amenity"="restaurant"]'],
    },

    "starbucks": {
        "category": "food_restaurants",
        "selectors": ['["amenity"="cafe"]'],
    },
    "espresso house": {
        "category": "food_restaurants",
        "selectors": ['["amenity"="cafe"]'],
    },
    "costa coffee": {
        "category": "food_restaurants",
        "selectors": ['["amenity"="cafe"]'],
    },
    "joe & the juice": {
        "category": "food_restaurants",
        "selectors": ['["amenity"="cafe"]', '["amenity"="fast_food"]'],
    },

    "kiwi": {
        "category": "retail_grocery",
        "selectors": ['["shop"="supermarket"]'],
    },
    "rema 1000": {
        "category": "retail_grocery",
        "selectors": ['["shop"="supermarket"]'],
    },
    "lidl": {
        "category": "retail_grocery",
        "selectors": ['["shop"="supermarket"]'],
    },
    "aldi": {
        "category": "retail_grocery",
        "selectors": ['["shop"="supermarket"]'],
    },
    "carrefour": {
        "category": "retail_grocery",
        "selectors": ['["shop"="supermarket"]', '["shop"="convenience"]'],
    },
    "albert heijn": {
        "category": "retail_grocery",
        "selectors": ['["shop"="supermarket"]'],
    },
    "tesco": {
        "category": "retail_grocery",
        "selectors": ['["shop"="supermarket"]', '["shop"="convenience"]'],
    },
    "ica": {
        "category": "retail_grocery",
        "selectors": ['["shop"="supermarket"]'],
    },
    "coop": {
        "category": "retail_grocery",
        "selectors": ['["shop"="supermarket"]', '["shop"="convenience"]'],
    },
    "7-eleven": {
        "category": "retail_grocery",
        "selectors": ['["shop"="convenience"]'],
    },
    "seven eleven": {
        "category": "retail_grocery",
        "selectors": ['["shop"="convenience"]'],
    },

    "circle k": {
        "category": "mobility_fuel",
        "selectors": ['["amenity"="fuel"]'],
    },
    "shell": {
        "category": "mobility_fuel",
        "selectors": ['["amenity"="fuel"]'],
    },
    "bp": {
        "category": "mobility_fuel",
        "selectors": ['["amenity"="fuel"]'],
    },
    "esso": {
        "category": "mobility_fuel",
        "selectors": ['["amenity"="fuel"]'],
    },
    "totalenergies": {
        "category": "mobility_fuel",
        "selectors": ['["amenity"="fuel"]'],
    },
    "okq8": {
        "category": "mobility_fuel",
        "selectors": ['["amenity"="fuel"]'],
    },
    "preem": {
        "category": "mobility_fuel",
        "selectors": ['["amenity"="fuel"]'],
    },

    "ikea": {
        "category": "retail_grocery",
        "selectors": ['["shop"="furniture"]'],
    },
    "h&m": {
        "category": "retail_grocery",
        "selectors": ['["shop"="clothes"]', '["shop"="fashion"]'],
    },
    "hm": {
        "category": "retail_grocery",
        "selectors": ['["shop"="clothes"]', '["shop"="fashion"]'],
    },
    "zara": {
        "category": "retail_grocery",
        "selectors": ['["shop"="clothes"]', '["shop"="fashion"]'],
    },
    "elgiganten": {
        "category": "retail_grocery",
        "selectors": ['["shop"="electronics"]'],
    },
    "media markt": {
        "category": "retail_grocery",
        "selectors": ['["shop"="electronics"]'],
    },
    "mediamarkt": {
        "category": "retail_grocery",
        "selectors": ['["shop"="electronics"]'],
    },

    "sats": {
        "category": "fitness_entertainment",
        "selectors": ['["leisure"="fitness_centre"]'],
    },
    "fitness24seven": {
        "category": "fitness_entertainment",
        "selectors": ['["leisure"="fitness_centre"]'],
    },
    "fitness 24 seven": {
        "category": "fitness_entertainment",
        "selectors": ['["leisure"="fitness_centre"]'],
    },
    "nordic wellness": {
        "category": "fitness_entertainment",
        "selectors": ['["leisure"="fitness_centre"]'],
    },
    "basic-fit": {
        "category": "fitness_entertainment",
        "selectors": ['["leisure"="fitness_centre"]'],
    },
    "basic fit": {
        "category": "fitness_entertainment",
        "selectors": ['["leisure"="fitness_centre"]'],
    },

    "scandic": {
        "category": "hotels",
        "selectors": ['["tourism"="hotel"]'],
    },
    "radisson": {
        "category": "hotels",
        "selectors": ['["tourism"="hotel"]'],
    },
    "best western": {
        "category": "hotels",
        "selectors": ['["tourism"="hotel"]'],
    },
    "marriott": {
        "category": "hotels",
        "selectors": ['["tourism"="hotel"]'],
    },
    "hilton": {
        "category": "hotels",
        "selectors": ['["tourism"="hotel"]'],
    },

    "boots": {
        "category": "healthcare_pharmacy",
        "selectors": ['["amenity"="pharmacy"]', '["shop"="chemist"]'],
    },
    "apoteket": {
        "category": "healthcare_pharmacy",
        "selectors": ['["amenity"="pharmacy"]'],
    },
    "lloydsapotek": {
        "category": "healthcare_pharmacy",
        "selectors": ['["amenity"="pharmacy"]'],
    },
    "lloyds apotek": {
        "category": "healthcare_pharmacy",
        "selectors": ['["amenity"="pharmacy"]'],
    },
    "walgreens": {
        "category": "healthcare_pharmacy",
        "selectors": ['["amenity"="pharmacy"]'],
    },

    "dhl": {
        "category": "services",
        "selectors": ['["amenity"="post_office"]', '["amenity"="parcel_locker"]'],
    },
    "ups": {
        "category": "services",
        "selectors": ['["amenity"="post_office"]', '["amenity"="parcel_locker"]'],
    },
    "fedex": {
        "category": "services",
        "selectors": ['["amenity"="post_office"]'],
    },
    "postnord": {
        "category": "services",
        "selectors": ['["amenity"="post_office"]', '["amenity"="parcel_locker"]'],
    },
    "instabox": {
        "category": "services",
        "selectors": ['["amenity"="parcel_locker"]'],
    },

    "nordea": {
        "category": "services",
        "selectors": ['["amenity"="bank"]', '["amenity"="atm"]'],
    },
    "seb": {
        "category": "services",
        "selectors": ['["amenity"="bank"]', '["amenity"="atm"]'],
    },
    "swedbank": {
        "category": "services",
        "selectors": ['["amenity"="bank"]', '["amenity"="atm"]'],
    },
    "handelsbanken": {
        "category": "services",
        "selectors": ['["amenity"="bank"]', '["amenity"="atm"]'],
    },
}

SMART_RULES = [
    {
        "category": "food_restaurants",
        "tokens": ["max", "burger", "hamburg", "mcdonald", "kfc", "subway", "taco", "pizza", "chicken", "grill", "kebab", "doner", "sushi"],
        "selectors": ['["amenity"="fast_food"]', '["amenity"="restaurant"]'],
    },
    {
        "category": "food_restaurants",
        "tokens": ["coffee", "espresso", "cafe", "café", "juice", "tea"],
        "selectors": ['["amenity"="cafe"]'],
    },
    {
        "category": "retail_grocery",
        "tokens": ["supermarket", "market", "grocery", "foods", "lidl", "aldi", "kiwi", "rema", "carrefour", "tesco", "spar", "ica", "coop"],
        "selectors": ['["shop"="supermarket"]', '["shop"="convenience"]'],
    },
    {
        "category": "retail_grocery",
        "tokens": ["fashion", "clothes", "zara", "h&m", "hm"],
        "selectors": ['["shop"="clothes"]', '["shop"="fashion"]'],
    },
    {
        "category": "retail_grocery",
        "tokens": ["electronics", "phone", "mobile", "media markt", "mediamarkt", "elgiganten"],
        "selectors": ['["shop"="electronics"]', '["shop"="mobile_phone"]', '["shop"="computer"]'],
    },
    {
        "category": "retail_grocery",
        "tokens": ["ikea", "furniture"],
        "selectors": ['["shop"="furniture"]'],
    },
    {
        "category": "mobility_fuel",
        "tokens": ["fuel", "gas", "petrol", "shell", "circle k", "esso", "bp", "okq8", "preem", "total"],
        "selectors": ['["amenity"="fuel"]'],
    },
    {
        "category": "mobility_fuel",
        "tokens": ["charge", "charging", "supercharger", "ionity", "tesla"],
        "selectors": ['["amenity"="charging_station"]'],
    },
    {
        "category": "mobility_fuel",
        "tokens": ["hertz", "avis", "europcar", "rental", "rent a car"],
        "selectors": ['["amenity"="car_rental"]'],
    },
    {
        "category": "hotels",
        "tokens": ["hotel", "hotels", "scandic", "radisson", "hilton", "marriott", "inn", "motel", "hostel"],
        "selectors": ['["tourism"="hotel"]', '["tourism"="motel"]', '["tourism"="hostel"]'],
    },
    {
        "category": "services",
        "tokens": ["bank", "nordea", "seb", "swedbank", "handelsbanken"],
        "selectors": ['["amenity"="bank"]', '["amenity"="atm"]'],
    },
    {
        "category": "services",
        "tokens": ["post", "dhl", "ups", "fedex", "parcel", "locker", "instabox", "postnord"],
        "selectors": ['["amenity"="post_office"]', '["amenity"="parcel_locker"]'],
    },
    {
        "category": "services",
        "tokens": ["hair", "barber", "beauty", "cosmetic", "sephora", "rituals", "cutters", "optician", "specsavers"],
        "selectors": ['["shop"="hairdresser"]', '["shop"="beauty"]', '["shop"="cosmetics"]', '["shop"="optician"]'],
    },
    {
        "category": "healthcare_pharmacy",
        "tokens": ["pharmacy", "apotek", "chemist", "boots", "walgreens", "clinic", "capio", "doctor", "dentist"],
        "selectors": ['["amenity"="pharmacy"]', '["shop"="chemist"]', '["amenity"="clinic"]', '["amenity"="dentist"]'],
    },
    {
        "category": "fitness_entertainment",
        "tokens": ["fitness", "gym", "sats", "wellness", "basic-fit", "sport"],
        "selectors": ['["leisure"="fitness_centre"]', '["leisure"="sports_centre"]'],
    },
    {
        "category": "fitness_entertainment",
        "tokens": ["cinema", "movie", "film", "theatre", "bowling"],
        "selectors": ['["amenity"="cinema"]', '["amenity"="theatre"]', '["leisure"="bowling_alley"]'],
    },
]


def log(message: str) -> None:
    print(message, flush=True)


def safe_filename(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9åäöæøéüß]+", "_", value, flags=re.I)
    return value.strip("_") or "export"


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


def infer_smart_selectors(chain: str, selected_category: str) -> list[str]:
    normalized = normalize_chain(chain)

    if normalized in KNOWN_CHAIN_SELECTORS:
        known = KNOWN_CHAIN_SELECTORS[normalized]

        if selected_category == "all" or selected_category == known["category"]:
            return known["selectors"]

    for rule in SMART_RULES:
        if selected_category != "all" and rule["category"] != selected_category:
            continue

        if any(token in normalized for token in rule["tokens"]):
            return rule["selectors"]

    return []


def get_query_plan(chain: str, selected_category: str) -> tuple[list[str], list[str], str]:
    if selected_category not in CATEGORY_SELECTORS:
        selected_category = "all"

    full_selectors = CATEGORY_SELECTORS[selected_category]
    smart_selectors = infer_smart_selectors(chain, selected_category)

    if smart_selectors:
        return smart_selectors, full_selectors, selected_category

    return full_selectors, full_selectors, selected_category


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
                        "User-Agent": "RetailAddressFinder/0.5 Smart B2C (GitHub Actions)",
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

    return {
        "chain_requested": chain,
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


def run_queries(country_iso: str, country_name: str, chain: str, selectors: list[str], phase_name: str) -> tuple[list[dict], int, list[str]]:
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
            rows.extend(mode_rows)
            rows = dedupe(rows)

            strict_count = sum(1 for r in mode_rows if r["address_quality"] == "strict")
            usable_count = sum(1 for r in mode_rows if r["address_quality"] == "usable")
            coord_count = sum(1 for r in mode_rows if r["address_quality"] == "coordinates_only")

            log(
                f"Added {len(mode_rows)} rows. "
                f"Strict: {strict_count}. "
                f"Usable: {usable_count}. "
                f"Coordinates only: {coord_count}. "
                f"Unique rows in phase: {len(rows)}."
            )

            time.sleep(0.4)

    return rows, total_elements, failed_queries


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
    selected_category = args.category.strip().lower()

    smart_selectors, fallback_selectors, selected_category = get_query_plan(chain, selected_category)

    log(f"Exporting B2C locations for '{chain}' in {country_name}")
    log(f"Selected category: {selected_category}")
    log(f"Aliases: {', '.join(get_chain_aliases(chain))}")

    rows = []
    total_elements = 0
    failed_queries = []

    rows_smart, elements_smart, failures_smart = run_queries(
        country_iso=country_iso,
        country_name=country_name,
        chain=chain,
        selectors=smart_selectors,
        phase_name="smart",
    )

    rows.extend(rows_smart)
    rows = dedupe(rows)
    total_elements += elements_smart
    failed_queries.extend(failures_smart)

    fallback_needed = len(rows) < 3 and fallback_selectors != smart_selectors

    if fallback_needed:
        log("\nSmart query returned fewer than 3 unique rows. Expanding to the full selected category.")
        remaining_selectors = [selector for selector in fallback_selectors if selector not in smart_selectors]

        rows_fallback, elements_fallback, failures_fallback = run_queries(
            country_iso=country_iso,
            country_name=country_name,
            chain=chain,
            selectors=remaining_selectors,
            phase_name="fallback",
        )

        rows.extend(rows_fallback)
        rows = dedupe(rows)
        total_elements += elements_fallback
        failed_queries.extend(failures_fallback)

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
