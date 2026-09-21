#!/usr/bin/env python3
"""Build postcode centroids from real OpenStreetMap address objects.

Input is a Sweden .osm.pbf extract, normally from Geofabrik.
The output is a compact JSON overlay keyed by 5-digit Swedish postcode.

This does NOT create official postcode boundaries. It creates a representative
point from the mean position of OSM objects carrying addr:postcode.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import osmium

POSTCODE_RE = re.compile(r"^(\d{3})\s?(\d{2})$")


def normalize_postcode(value: str | None) -> str | None:
    if not value:
        return None
    match = POSTCODE_RE.match(str(value).strip())
    if not match:
        return None
    return "".join(match.groups())


class Aggregate:
    __slots__ = ("count", "sum_lat", "sum_lon", "min_lat", "max_lat", "min_lon", "max_lon", "cities")

    def __init__(self) -> None:
        self.count = 0
        self.sum_lat = 0.0
        self.sum_lon = 0.0
        self.min_lat = 90.0
        self.max_lat = -90.0
        self.min_lon = 180.0
        self.max_lon = -180.0
        self.cities: Counter[str] = Counter()

    def add(self, lat: float, lon: float, city: str = "") -> None:
        if not (math.isfinite(lat) and math.isfinite(lon)):
            return
        # Broad Sweden guard. Keeps obvious bad/out-of-country tags out.
        if not (54.0 <= lat <= 70.0 and 9.0 <= lon <= 25.0):
            return
        self.count += 1
        self.sum_lat += lat
        self.sum_lon += lon
        self.min_lat = min(self.min_lat, lat)
        self.max_lat = max(self.max_lat, lat)
        self.min_lon = min(self.min_lon, lon)
        self.max_lon = max(self.max_lon, lon)
        if city:
            self.cities[city] += 1

    def as_dict(self, code: str) -> dict:
        lat = self.sum_lat / self.count
        lon = self.sum_lon / self.count
        city = self.cities.most_common(1)[0][0] if self.cities else ""
        return {
            "code": code,
            "lat": round(lat, 7),
            "lng": round(lon, 7),
            "samples": self.count,
            "city": city,
            "bbox": [
                round(self.min_lat, 6),
                round(self.min_lon, 6),
                round(self.max_lat, 6),
                round(self.max_lon, 6),
            ],
        }


class AddressPostcodeHandler(osmium.SimpleHandler):
    def __init__(self) -> None:
        super().__init__()
        self.aggregates: dict[str, Aggregate] = defaultdict(Aggregate)
        self.tagged_objects = 0

    def _add(self, tags, lat: float, lon: float) -> None:
        code = normalize_postcode(tags.get("addr:postcode"))
        if not code:
            return
        city = str(tags.get("addr:city") or tags.get("addr:place") or "").strip()
        before = self.aggregates[code].count
        self.aggregates[code].add(lat, lon, city)
        if self.aggregates[code].count > before:
            self.tagged_objects += 1

    def node(self, node) -> None:
        if "addr:postcode" not in node.tags:
            return
        try:
            if node.location.valid():
                self._add(node.tags, node.location.lat, node.location.lon)
        except osmium.InvalidLocationError:
            return

    def way(self, way) -> None:
        if "addr:postcode" not in way.tags:
            return

        coords = []
        for ref in way.nodes:
            try:
                if ref.location.valid():
                    coords.append((ref.location.lat, ref.location.lon))
            except osmium.InvalidLocationError:
                continue

        if not coords:
            return

        lat = sum(value[0] for value in coords) / len(coords)
        lon = sum(value[1] for value in coords) / len(coords)
        self._add(way.tags, lat, lon)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pbf")
    parser.add_argument("out")
    args = parser.parse_args()

    source = Path(args.pbf)
    out = Path(args.out)

    handler = AddressPostcodeHandler()
    handler.apply_file(str(source), locations=True, idx="flex_mem")

    rows = [
        aggregate.as_dict(code)
        for code, aggregate in handler.aggregates.items()
        if aggregate.count > 0
    ]
    rows.sort(key=lambda row: row["code"])

    if len(rows) < 3000:
        raise RuntimeError(
            f"Refusing suspiciously small OSM postcode overlay: {len(rows)} unique codes"
        )

    payload = {
        "meta": {
            "source": "OpenStreetMap address objects via Geofabrik Sweden extract",
            "sourceUrl": "https://download.geofabrik.de/europe/sweden.html",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "license": "ODbL 1.0",
            "attribution": "© OpenStreetMap contributors",
            "taggedObjects": handler.tagged_objects,
            "uniquePostcodes": len(rows),
            "method": "Mean center of OSM nodes/ways carrying addr:postcode for each five-digit Swedish postcode.",
        },
        "postcodes": rows,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    print(
        f"Wrote {len(rows)} postcode centroids from {handler.tagged_objects} OSM address objects to {out}"
    )


if __name__ == "__main__":
    main()
