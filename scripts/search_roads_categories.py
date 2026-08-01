"""Search road KMZ files for roundabouts and other categories."""
from __future__ import annotations

import json
import re
import zipfile
from collections import Counter
from html import unescape
from pathlib import Path

FILES = [
    Path(r"C:\Users\Eng Abdelatif\Downloads\Prince Mohammed Bin Salman Road.kmz"),
    Path(r"C:\Users\Eng Abdelatif\Downloads\اللوحات_التحذيرية.kmz"),
]
OUT = Path(__file__).resolve().parent / "roads_kmz_categories.json"

KEYWORDS = [
    "بلدور", "دوار", "تقاطع", "مفترق", "جسر", "نفق", "ممر", "جسر",
    "roundabout", "intersection", "bridge", "tunnel", "ramp", "exit",
    "تصنيف", "نوع", "فئة", "type", "category", "class",
]


def plain(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def read_kml(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        return z.read(next(n for n in z.namelist() if n.lower().endswith(".kml"))).decode(
            "utf-8", errors="replace"
        )


def all_folder_names(kml: str) -> list[str]:
    names = []
    for match in re.finditer(r"<Folder\b[^>]*>(.*?)</Folder>", kml, re.S | re.I):
        block = match.group(1)
        name_match = re.search(r"<name>(.*?)</name>", block, re.S | re.I)
        if name_match:
            names.append(plain(name_match.group(1)))
    return names


def inspect(path: Path) -> dict:
    kml = read_kml(path)
    placemarks = re.findall(r"<Placemark\b[^>]*>.*?</Placemark>", kml, re.S | re.I)

    names: Counter[str] = Counter()
    name_text_hits: Counter[str] = Counter()
    desc_field_values: dict[str, Counter[str]] = {}
    keyword_hits: dict[str, list[str]] = {k: [] for k in KEYWORDS}
    document_name = plain(re.search(r"<Document>.*?<name>(.*?)</name>", kml, re.S | re.I).group(1) if re.search(r"<Document>.*?<name>", kml, re.S | re.I) else "")
    style_ids: Counter[str] = Counter()

    for block in placemarks:
        name_match = re.search(r"<name>(.*?)</name>", block, re.S | re.I)
        name = plain(name_match.group(1) if name_match else "")
        names[name] += 1

        for kw in KEYWORDS:
            if kw.lower() in name.lower() or kw in name:
                keyword_hits[kw].append(name)

        desc_match = re.search(r"<description>(.*?)</description>", block, re.S | re.I)
        desc_text = plain(desc_match.group(1) if desc_match else "")
        for kw in KEYWORDS:
            if kw.lower() in desc_text.lower() or kw in desc_text:
                keyword_hits[kw].append(name or desc_text[:80])

        if desc_match:
            pairs = re.findall(
                r"<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>",
                desc_match.group(1),
                re.I | re.S,
            )
            for key, value in pairs:
                key = plain(key)
                value = plain(value)
                if not key:
                    continue
                desc_field_values.setdefault(key, Counter())[value] += 1

        for style in re.findall(r"id=['\"]([^'\"]+)['\"]", block):
            if "Style" in style:
                style_ids[style] += 1

        style_url = re.search(r"<styleUrl>(.*?)</styleUrl>", block, re.I)
        if style_url:
            style_ids[plain(style_url.group(1))] += 1

    # meaningful unique field values (exclude coords and shape noise)
    meaningful_fields = {}
    skip_substrings = ("SHAPE", "Start_", "END_", "START_", "خط ")
    for field, values in desc_field_values.items():
        if any(s in field for s in skip_substrings):
            continue
        if len(values) <= 50:
            meaningful_fields[field] = dict(values.most_common(30))

    non_numeric_names = [n for n in names if not re.fullmatch(r"\d+", n)]

    return {
        "document_name": document_name,
        "placemark_count": len(placemarks),
        "folder_names": sorted(set(all_folder_names(kml))),
        "unique_name_count": len(names),
        "non_numeric_names_sample": non_numeric_names[:50],
        "non_numeric_name_count": len(non_numeric_names),
        "style_ids": dict(style_ids.most_common(20)),
        "meaningful_fields": meaningful_fields,
        "keyword_hits": {k: list(dict.fromkeys(v))[:10] for k, v in keyword_hits.items() if v},
    }


def main() -> None:
    report = {path.name: inspect(path) for path in FILES}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written {OUT}")


if __name__ == "__main__":
    main()
