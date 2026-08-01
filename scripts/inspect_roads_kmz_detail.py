"""Detailed inspection of Prince Mohammed road KMZ segments."""
from __future__ import annotations

import json
import re
import zipfile
from collections import Counter
from html import unescape
from pathlib import Path

PATH = Path(r"C:\Users\Eng Abdelatif\Downloads\Prince Mohammed Bin Salman Road.kmz")
OUT = Path(__file__).resolve().parent / "roads_kmz_detail.json"


def plain(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    with zipfile.ZipFile(PATH) as z:
        kml = z.read(next(n for n in z.namelist() if n.lower().endswith(".kml"))).decode(
            "utf-8", errors="replace"
        )

    placemarks = re.findall(r"<Placemark\b[^>]*>.*?</Placemark>", kml, re.S | re.I)
    by_name: dict[str, list[dict]] = {}

    for block in placemarks:
        name_match = re.search(r"<name>(.*?)</name>", block, re.S | re.I)
        name = plain(name_match.group(1) if name_match else "")
        if "<Point" in block:
            geom = "Point"
        elif "<LineString" in block:
            geom = "LineString"
        elif "<Polygon" in block:
            geom = "Polygon"
        else:
            geom = "other"

        attrs: dict[str, str] = {}
        desc_match = re.search(r"<description>(.*?)</description>", block, re.S | re.I)
        if desc_match:
            pairs = re.findall(
                r"<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>",
                desc_match.group(1),
                re.I | re.S,
            )
            for key, value in pairs:
                key = plain(key)
                value = plain(value)
                if key and key not in attrs:
                    attrs[key] = value

        style_match = re.search(r"<styleUrl>(.*?)</styleUrl>", block, re.I)
        style = plain(style_match.group(1) if style_match else "")

        by_name.setdefault(name, []).append({"geom": geom, "style": style, "attrs": attrs})

    combo: Counter[str] = Counter()
    useful_attrs: Counter[tuple[str, str]] = Counter()
    skip_keys = {"Start_X", "Start_Y", "END_X", "END_Y", "START_Y"}

    for _name, items in by_name.items():
        geoms = "+".join(sorted(item["geom"] for item in items))
        combo[geoms] += 1
        for item in items:
            for key, value in item["attrs"].items():
                if (
                    value
                    and value not in ("<Null>", "&lt;Null&gt;")
                    and "SHAPE" not in key
                    and key not in skip_keys
                ):
                    useful_attrs[(key, value)] += 1

    out = {
        "segment_count": len(by_name),
        "geometry_combos_per_segment": dict(combo),
        "useful_attribute_values": [
            {"field": key, "value": value, "count": count}
            for (key, value), count in useful_attrs.most_common(50)
        ],
        "sample_segment_1": by_name.get("1", []),
        "line_only_attrs_keys": sorted(
            {
                key
                for item in by_name.values()
                for sub in item
                if sub["geom"] == "LineString"
                for key in sub["attrs"]
            }
        ),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written {OUT}")


if __name__ == "__main__":
    main()
