"""Convert axis KMZ layers (roads, lighting, signs) and export bridges."""
from __future__ import annotations

import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "static" / "data"
NS = {"k": "http://www.opengis.net/kml/2.2"}

AXIS_ROADS_KMZ = Path(
    r"C:\Users\Eng Abdelatif\Downloads\محور الامير محمد بن سلمان.kmz"
)
LIGHTING_KMZ = Path(
    r"C:\Users\Eng Abdelatif\Downloads\شبكة الإنارة بمحور طريق الأمير محمد بن سلمان من الحرب حتى كبري بحرة.kmz"
)
SIGNS_KMZ = Path(
    r"C:\Users\Eng Abdelatif\Downloads\اللوحات الارشادية طريق الامير محمد بن سلمان (1).kmz"
)

ROADS_COLOR = "#38bdf8"
LIGHTING_LINE_COLOR = "#fbbf24"
LIGHTING_POINT_COLOR = "#fde047"
SIGNS_COLOR = "#fb923c"
BRIDGES_COLOR = "#c084fc"
DIR_LABELS = {"N": "شمال", "S": "جنوب", "E": "شرق", "W": "غرب"}


def read_kml(kmz: Path) -> str:
    with zipfile.ZipFile(kmz) as z:
        kml_name = next(n for n in z.namelist() if n.lower().endswith(".kml"))
        return z.read(kml_name).decode("utf-8", errors="replace")


def parse_description(html: str) -> dict:
    html = unescape(html or "")
    pairs = re.findall(r"<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>", html, re.I | re.S)
    row: dict[str, str] = {}
    for k, v in pairs:
        k = re.sub(r"<[^>]+>", "", k).strip()
        v = re.sub(r"<[^>]+>", "", v).strip()
        if not k or k in row:
            continue
        if v in ("<Null>", "&lt;Null&gt;", ""):
            v = ""
        row[k] = v
    return row


def plain_text(value: str) -> str:
    text = unescape(value or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_coords(text: str) -> list[list[float]]:
    coords: list[list[float]] = []
    for token in (text or "").split():
        parts = token.split(",")
        if len(parts) >= 2:
            lng, lat = float(parts[0]), float(parts[1])
            coords.append([lng, lat])
    return coords


def parse_simple_data(block: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for name, value in re.findall(
        r"<SimpleData\s+name=['\"]([^'\"]+)['\"]>(.*?)</SimpleData>", block, re.S | re.I
    ):
        data[name] = plain_text(value)
    return data


def iter_placemark_blocks(kml: str):
    for block in re.findall(r"<Placemark\b[^>]*>.*?</Placemark>", kml, re.S | re.I):
        yield block


def geom_type(block: str) -> str | None:
    for tag in ("LineString", "Point", "Polygon"):
        if re.search(rf"<{tag}\b", block, re.I):
            return tag
    return None


def extract_coords(block: str) -> list[list[float]]:
    coords_el = re.search(r"<coordinates>(.*?)</coordinates>", block, re.S | re.I)
    if not coords_el:
        return []
    return parse_coords(coords_el.group(1))


def lighting_kind(desc: str, style: str) -> str:
    text = desc or ""
    if "برج" in text or "target12" in style or "target3" in style:
        return "برج"
    if "عامود" in text or "target5" in style:
        return "عمود"
    if "فانوس" in text or "فوانيس" in text:
        return "فانوس"
    if "تقاطع" in text:
        return "تقاطع"
    return "نقطة إنارة"


def polygon_rings(pm) -> list[list[list[float]]]:
    rings: list[list[list[float]]] = []
    for polygon in pm.findall(".//k:Polygon", NS):
        ring_el = polygon.find(".//k:outerBoundaryIs//k:LinearRing/k:coordinates", NS)
        if ring_el is None or not ring_el.text:
            continue
        ring = parse_coords(ring_el.text)
        if len(ring) >= 3:
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            rings.append(ring)
    return rings


def convert_axis_roads() -> dict:
    kml = read_kml(AXIS_ROADS_KMZ)
    root = ET.fromstring(kml.encode("utf-8"))
    features = []
    for pm in root.findall(".//k:Placemark", NS):
        name_el = pm.find("k:name", NS)
        name = (name_el.text or "").strip()
        desc_el = pm.find("k:description", NS)
        attrs = parse_description(desc_el.text if desc_el is not None else "")
        rings = polygon_rings(pm)
        if not rings:
            continue
        props = {
            "layer": "roads",
            "name": attrs.get("Road_Name", name) or name,
            "road_id": attrs.get("SEC_ID", "") or attrs.get("Global_ID", ""),
            "municipality": attrs.get("MUNICIPALI", ""),
            "district": attrs.get("District_N", ""),
            "length_m": attrs.get("True_Lengh", "") or attrs.get("SHAPE_Leng", ""),
            "type": attrs.get("Type", "") or attrs.get("تصنيف", ""),
            "color": ROADS_COLOR,
        }
        geometry = (
            {"type": "Polygon", "coordinates": rings}
            if len(rings) == 1
            else {"type": "MultiPolygon", "coordinates": [[r] for r in rings]}
        )
        features.append({"type": "Feature", "geometry": geometry, "properties": props})
    return {"type": "FeatureCollection", "features": features}


def convert_lighting() -> dict:
    kml = read_kml(LIGHTING_KMZ)
    features = []
    for block in iter_placemark_blocks(kml):
        gtype = geom_type(block)
        if not gtype:
            continue
        coords = extract_coords(block)
        if not coords:
            continue
        name_m = re.search(r"<name>(.*?)</name>", block, re.S | re.I)
        desc_m = re.search(r"<description>(.*?)</description>", block, re.S | re.I)
        style_m = re.search(r"<styleUrl>(.*?)</styleUrl>", block, re.S | re.I)
        name = plain_text(name_m.group(1) if name_m else "")
        desc = plain_text(desc_m.group(1) if desc_m else "")
        style = style_m.group(1).strip() if style_m else ""
        kind = lighting_kind(desc, style)
        if gtype == "LineString" and len(coords) < 2:
            continue
        props = {
            "layer": "lighting",
            "name": name or kind,
            "kind": kind,
            "description": desc,
            "color": LIGHTING_LINE_COLOR if gtype == "LineString" else LIGHTING_POINT_COLOR,
        }
        if gtype == "Point":
            geometry = {"type": "Point", "coordinates": coords[0]}
        else:
            geometry = {"type": "LineString", "coordinates": coords}
        features.append({"type": "Feature", "geometry": geometry, "properties": props})
    return {"type": "FeatureCollection", "features": features}


def convert_signs() -> dict:
    kml = read_kml(SIGNS_KMZ)
    features = []
    for block in iter_placemark_blocks(kml):
        if geom_type(block) != "Point":
            continue
        coords = extract_coords(block)
        if not coords:
            continue
        ext_m = re.search(r"<ExtendedData>(.*?)</ExtendedData>", block, re.S | re.I)
        ext = parse_simple_data(ext_m.group(1)) if ext_m else {}
        props = {
            "layer": "signs",
            "name": "لوحة إرشادية",
            "color": SIGNS_COLOR,
            "x": ext.get("x", ""),
            "y": ext.get("y", ""),
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": coords[0]},
                "properties": props,
            }
        )
    return {"type": "FeatureCollection", "features": features}


def convert_bridges() -> dict:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, str(ROOT))
    import django

    django.setup()
    from bridges.models import Bridge

    features = []
    for bridge in Bridge.objects.all().order_by("id"):
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [bridge.lng, bridge.lat]},
                "properties": {
                    "layer": "bridges",
                    "name": bridge.name,
                    "color": BRIDGES_COLOR,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def write_geojson(path: Path, data: dict) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return len(data.get("features", []))


def main():
    counts = {
        "roads": write_geojson(DATA / "axis-roads.geojson", convert_axis_roads()),
        "lighting": write_geojson(DATA / "axis-lighting.geojson", convert_lighting()),
        "signs": write_geojson(DATA / "axis-signs.geojson", convert_signs()),
        "bridges": write_geojson(DATA / "axis-bridges.geojson", convert_bridges()),
    }
    print(counts)


if __name__ == "__main__":
    main()
