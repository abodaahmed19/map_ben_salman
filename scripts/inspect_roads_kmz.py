"""Inspect roads KMZ files for classifications and structure."""
from __future__ import annotations

import json
import re
import zipfile
from collections import Counter, defaultdict
from html import unescape
from pathlib import Path

FILES = [
    Path(r"C:\Users\Eng Abdelatif\Downloads\Prince Mohammed Bin Salman Road.kmz"),
    Path(r"C:\Users\Eng Abdelatif\Downloads\اللوحات_التحذيرية.kmz"),
]
OUT = Path(__file__).resolve().parent / "roads_kmz_inspect.json"


def read_kml(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        kml_name = next(n for n in z.namelist() if n.lower().endswith(".kml"))
        return z.read(kml_name).decode("utf-8", errors="replace")


def plain(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_desc(html: str) -> dict[str, str]:
    html = unescape(html or "")
    pairs = re.findall(r"<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>", html, re.I | re.S)
    row: dict[str, str] = {}
    for key, value in pairs:
        key = re.sub(r"<[^>]+>", "", key).strip()
        value = re.sub(r"<[^>]+>", "", value).strip()
        if key and key not in row:
            row[key] = value
    return row


def geom_type(block: str) -> str:
    for tag in ("LineString", "Point", "Polygon", "MultiGeometry"):
        if re.search(rf"<{tag}\b", block, re.I):
            return tag
    return "unknown"


def inspect_file(path: Path) -> dict:
    if not path.exists():
        return {"error": "file not found", "path": str(path)}

    kml = read_kml(path)
    placemarks = re.findall(r"<Placemark\b[^>]*>.*?</Placemark>", kml, re.S | re.I)
    doc_folders = re.findall(r"<Folder>\s*<name>(.*?)</name>", kml, re.S | re.I)
    folder_names = [plain(x) for x in doc_folders]

    geoms: Counter[str] = Counter()
    desc_keys: Counter[str] = Counter()
    desc_values_by_key: dict[str, Counter[str]] = defaultdict(Counter)
    simple_data_keys: Counter[str] = Counter()
    styles: Counter[str] = Counter()
    names: list[str] = []

    for block in placemarks:
        name_match = re.search(r"<name>(.*?)</name>", block, re.S | re.I)
        names.append(plain(name_match.group(1) if name_match else ""))
        geoms[geom_type(block)] += 1

        desc_match = re.search(r"<description>(.*?)</description>", block, re.S | re.I)
        attrs = parse_desc(desc_match.group(1) if desc_match else "")
        for key, value in attrs.items():
            desc_keys[key] += 1
            cleaned = plain(value)
            if cleaned and cleaned not in ("<Null>", "&lt;Null&gt;"):
                desc_values_by_key[key][cleaned] += 1

        for name, _ in re.findall(
            r"<SimpleData\s+name=['\"]([^'\"]+)['\"]>(.*?)</SimpleData>",
            block,
            re.S | re.I,
        ):
            simple_data_keys[name] += 1

        style_match = re.search(r"<styleUrl>(.*?)</styleUrl>", block, re.I)
        if style_match:
            styles[plain(style_match.group(1))] += 1

    classification_fields = {}
    for key, values in desc_values_by_key.items():
        key_lower = key.lower()
        is_classification = any(
            token in key_lower
            for token in ("type", "تصنيف", "class", "category", "kind", "نوع")
        )
        if is_classification or len(values) <= 30:
            classification_fields[key] = dict(values.most_common(30))

    return {
        "path": str(path),
        "placemark_count": len(placemarks),
        "geometry_types": dict(geoms),
        "folder_names": sorted(set(folder_names)),
        "folder_count": len(set(folder_names)),
        "description_fields": dict(desc_keys),
        "classification_fields": classification_fields,
        "simpledata_fields": dict(simple_data_keys),
        "style_urls_top": dict(styles.most_common(20)),
        "name_samples": [n for n in names[:20] if n],
    }


def main() -> None:
    report = {path.name: inspect_file(path) for path in FILES}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written {OUT}")


if __name__ == "__main__":
    main()
