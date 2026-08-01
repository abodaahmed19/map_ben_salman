"""Convert axis KMZ layers (roads, lighting, signs) and export bridges."""
from __future__ import annotations

import json
import re
import zipfile
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "static" / "data"
NS = {"k": "http://www.opengis.net/kml/2.2"}

AXIS_ROADS_KMZ = Path(
    r"C:\Users\Eng Abdelatif\Downloads\Prince Mohammed Bin Salman Road.kmz"
)
WARN_SIGNS_KMZ = Path(
    r"C:\Users\Eng Abdelatif\Downloads\اللوحات_التحذيرية.kmz"
)
BRIDGES_XLSX = Path(
    r"C:\Users\Eng Abdelatif\Downloads\جسور MBS محور الأمير محمد بن سلمان tariq.xlsx"
)
LIGHTING_KMZ = Path(
    r"C:\Users\Eng Abdelatif\Downloads\شبكة الإنارة بمحور طريق الأمير محمد بن سلمان من الحرب حتى كبري بحرة (1).kmz"
)
SIGNS_KMZ = Path(
    r"C:\Users\Eng Abdelatif\Downloads\اللوحات الارشادية طريق الامير محمد بن سلمان (1).kmz"
)

ROADS_COLOR = "#38bdf8"
ROAD_CATEGORY_COLORS = {
    "البردورات": "#38bdf8",
    "الأرصفة": "#0ea5e9",
    "الأحداثيات": "#7dd3fc",
    "لوحات تحذيرية": "#fb923c",
}
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


def _cell_value(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in ("nan", "none"):
        return ""
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return text


ROAD_POPUP_SKIP = {
    "layer",
    "color",
    "Start_X",
    "Start_Y",
    "START_Y",
    "END_X",
    "END_Y",
    "خط الطول للنقطة",
    "خط العرض للنقطة",
    "خط طول البداية",
    "خط عرض البداية",
    "خط طول النهاية",
    "خط عرض النهاية",
}


def _clean_desc_key(key: str) -> str:
    key = re.sub(r"\s+", " ", key or "").strip()
    key = re.sub(r"^\d+\s*SHAPE$", "SHAPE", key)
    return key


def _placemark_description(pm: ET.Element) -> dict[str, str]:
    desc_el = pm.find("k:description", NS)
    if desc_el is None or not desc_el.text:
        return {}
    attrs = parse_description(desc_el.text)
    cleaned: dict[str, str] = {}
    for key, value in attrs.items():
        name = _clean_desc_key(key)
        if name in ROAD_POPUP_SKIP or "SHAPE" in name:
            continue
        value = plain_text(value)
        if value in ("<Null>", "&lt;Null&gt;", "None"):
            value = ""
        if value:
            cleaned[name] = value
    return cleaned


def _point_coords(pm: ET.Element) -> list[float] | None:
    el = pm.find(".//k:Point/k:coordinates", NS)
    if el is None or not el.text:
        return None
    coords = parse_coords(el.text)
    return coords[0] if coords else None


def _line_coords(pm: ET.Element) -> list[list[float]] | None:
    el = pm.find(".//k:LineString/k:coordinates", NS)
    if el is None or not el.text:
        return None
    coords = parse_coords(el.text)
    return coords if len(coords) >= 2 else None


def _polygon_coords(pm: ET.Element) -> list[list[float]] | None:
    rings = polygon_rings(pm)
    if not rings:
        return None
    return rings[0]


def _placemark_geometry(pm: ET.Element) -> dict | None:
    if pm.find(".//k:Point", NS) is not None:
        coords = _point_coords(pm)
        return {"type": "Point", "coordinates": coords} if coords else None
    if pm.find(".//k:LineString", NS) is not None:
        coords = _line_coords(pm)
        return {"type": "LineString", "coordinates": coords} if coords else None
    if pm.find(".//k:Polygon", NS) is not None:
        ring = _polygon_coords(pm)
        return {"type": "Polygon", "coordinates": [ring]} if ring else None
    return None


def _road_feature(pm: ET.Element, category: str) -> dict | None:
    geometry = _placemark_geometry(pm)
    if not geometry:
        return None

    name_el = pm.find("k:name", NS)
    name = (name_el.text or "").strip() if name_el is not None else ""
    attrs = _placemark_description(pm)
    road_name = attrs.get("اسم الطريق") or attrs.get("اسم_الطريق") or ""
    title = name or road_name or category

    props = {
        "layer": "roads",
        "category": category,
        "name": title,
        "color": ROAD_CATEGORY_COLORS.get(category, ROADS_COLOR),
    }
    for key, value in attrs.items():
        if key not in props and key not in ROAD_POPUP_SKIP:
            props[key] = value

    return {"type": "Feature", "geometry": geometry, "properties": props}


def _iter_folder_placemarks(folder: ET.Element, category: str) -> list[dict]:
    features: list[dict] = []
    for pm in folder.findall("k:Placemark", NS):
        feature = _road_feature(pm, category)
        if feature:
            features.append(feature)
    for child in folder.findall("k:Folder", NS):
        name_el = child.find("k:name", NS)
        child_name = (name_el.text or "").strip() if name_el is not None else category
        features.extend(_iter_folder_placemarks(child, child_name))
    return features


def _convert_prince_road_kmz() -> list[dict]:
    with zipfile.ZipFile(AXIS_ROADS_KMZ) as z:
        kml = z.read(next(n for n in z.namelist() if n.lower().endswith(".kml")))
    root = ET.fromstring(kml)
    doc = root.find(".//k:Document", NS)
    if doc is None:
        return []

    features: list[dict] = []
    for folder in doc.findall("k:Folder", NS):
        name_el = folder.find("k:name", NS)
        folder_name = (name_el.text or "").strip() if name_el is not None else ""
        features.extend(_iter_folder_placemarks(folder, folder_name))
    return features


def _convert_warning_signs_kmz() -> list[dict]:
    kml = read_kml(WARN_SIGNS_KMZ)
    features: list[dict] = []
    for block in iter_placemark_blocks(kml):
        if geom_type(block) != "Point":
            continue
        coords = extract_coords(block)
        if not coords:
            continue

        name_m = re.search(r"<name>(.*?)</name>", block, re.S | re.I)
        name = plain_text(name_m.group(1) if name_m else "")
        desc_m = re.search(r"<description>(.*?)</description>", block, re.S | re.I)
        attrs = parse_description(desc_m.group(1) if desc_m else "")

        props = {
            "layer": "roads",
            "category": "لوحات تحذيرية",
            "name": name or attrs.get("معرف الأصل", "") or "لوحة تحذيرية",
            "color": ROAD_CATEGORY_COLORS["لوحات تحذيرية"],
        }
        for key, value in attrs.items():
            clean_key = str(key).strip()
            if clean_key in ROAD_POPUP_SKIP:
                continue
            clean_val = plain_text(value)
            if clean_val and clean_val not in ("<Null>", "&lt;Null&gt;", "None"):
                props[clean_key] = clean_val

        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": coords[0]},
                "properties": props,
            }
        )
    return features


def convert_axis_roads() -> dict:
    features = _convert_prince_road_kmz() + _convert_warning_signs_kmz()
    return {"type": "FeatureCollection", "features": features}


def convert_bridges() -> dict:
    import pandas as pd

    df = pd.read_excel(BRIDGES_XLSX, sheet_name=0)
    lng_col = "خط الطول للنقطة"
    lat_col = "خط العرض للنقطة"
    name_col = "معرف الأصل"
    features = []
    for _, row in df.iterrows():
        lng = row.get(lng_col)
        lat = row.get(lat_col)
        if pd.isna(lng) or pd.isna(lat):
            continue
        props = {
            "layer": "bridges",
            "name": _cell_value(row.get(name_col)),
            "color": BRIDGES_COLOR,
        }
        for col in df.columns:
            col_name = str(col).strip()
            if col_name in (lng_col, lat_col):
                continue
            value = _cell_value(row.get(col))
            if not value:
                continue
            if col_name == name_col:
                continue
            props[col_name] = value
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(lng), float(lat)]},
                "properties": props,
            }
        )
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
