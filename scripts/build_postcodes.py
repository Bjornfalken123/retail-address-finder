#!/usr/bin/env python3
"""Build a deterministic static Swedish postcode point dataset from GeoNames.

Source: https://download.geonames.org/export/zip/SE.zip
License: CC BY 4.0 (attribution required): https://www.geonames.org/
"""

from __future__ import annotations

import csv
import io
import json
import math
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

SOURCE_URL = "https://download.geonames.org/export/zip/SE.zip"
OUT = Path("public/data/postcodes-se.json")


def clean_code(value: str) -> str | None:
    digits = "".join(ch for ch in value if ch.isdigit())
    return digits if len(digits) == 5 else None


def as_accuracy(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def most_common_nonempty(values: list[str]) -> str:
    values = [v.strip() for v in values if v and v.strip()]
    return Counter(values).most_common(1)[0][0] if values else ""


def main() -> None:
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "retail-address-finder-postcode-sync/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        archive_bytes = response.read()
        source_last_modified = response.headers.get("Last-Modified", "")

    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        raw = archive.read("SE.txt").decode("utf-8")

    groups: dict[str, list[dict]] = defaultdict(list)
    source_rows = 0

    for row in csv.reader(io.StringIO(raw), delimiter="\t"):
        if len(row) < 11:
            continue

        code = clean_code(row[1])
        if not code:
            continue

        try:
            lat = float(row[9])
            lng = float(row[10])
        except (TypeError, ValueError):
            continue

        if not (math.isfinite(lat) and math.isfinite(lng)):
            continue

        source_rows += 1
        groups[code].append(
            {
                "city": row[2].strip(),
                "county": row[3].strip(),
                "municipality": row[5].strip(),
                "lat": lat,
                "lng": lng,
                "accuracy": as_accuracy(row[11] if len(row) > 11 else ""),
            }
        )

    postcodes = []
    for code, entries in groups.items():
        max_accuracy = max(entry["accuracy"] for entry in entries)
        best = [entry for entry in entries if entry["accuracy"] == max_accuracy]
        lat = sum(entry["lat"] for entry in best) / len(best)
        lng = sum(entry["lng"] for entry in best) / len(best)

        postcodes.append(
            {
                "code": code,
                "city": most_common_nonempty([entry["city"] for entry in best]),
                "county": most_common_nonempty([entry["county"] for entry in best]),
                "municipality": most_common_nonempty(
                    [entry["municipality"] for entry in best]
                ),
                "lat": round(lat, 7),
                "lng": round(lng, 7),
                "accuracy": max_accuracy,
                "sourceRows": len(entries),
            }
        )

    postcodes.sort(key=lambda item: item["code"])

    # Flag coordinates shared by many postcodes. This is useful because a shared
    # place centroid is less precise for radius-based targeting than a dedicated
    # postcode coordinate.
    coordinate_counts = Counter(
        (round(item["lat"], 5), round(item["lng"], 5)) for item in postcodes
    )
    for item in postcodes:
        item["sharedCoordinateCount"] = coordinate_counts[
            (round(item["lat"], 5), round(item["lng"], 5))
        ]

    payload = {
        "meta": {
            "source": "GeoNames Swedish postal code dump (SE.zip)",
            "sourceUrl": SOURCE_URL,
            "sourceLastModified": source_last_modified,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "license": "CC BY 4.0",
            "attributionUrl": "https://www.geonames.org/",
            "sourceRows": source_rows,
            "uniquePostcodes": len(postcodes),
            "method": (
                "One point per 5-digit postcode. When GeoNames has multiple rows "
                "for a code, rows with the highest accuracy are retained and their "
                "coordinates are averaged."
            ),
        },
        "postcodes": postcodes,
    }

    if len(postcodes) < 5000:
        raise RuntimeError(
            f"Refusing to publish suspiciously small dataset: {len(postcodes)} postcodes"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    print(
        f"Wrote {len(postcodes)} unique postcodes from {source_rows} GeoNames rows to {OUT}"
    )


if __name__ == "__main__":
    main()
