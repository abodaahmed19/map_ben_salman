"""Convert axis-assets KMZ to GeoJSON with parsed segment attributes."""
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import Path

KMZ = Path(r"C:\Users\Eng Abdelatif\Downloads\طريق الأمير محمد بن سلمانkmz\طريق الأمير محمد بن سلمانkmz.kmz")
OUT = Path(__file__).resolve().parent.parent / "static" / "data" / "axis-assets.geojson"
NS = {"k": "http://www.opengis.net/kml/2.2"}

STREET_COLORS = {
    "طريق الحرمين": "#f59e0b",
    "طريق جدة_مكة": "#38bdf8",
    "طريق الفلاح": "#a78bfa",
}
DIR_LABELS = {"N": "شمال", "S": "جنوب", "E": "شرق", "W": "غرب"}


def parse_description(html: str) -> dict:
    html = unescape(html or "")
    pairs = re.findall(r"<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>", html, re.I | re.S)
    row = {}
    for k, v in pairs:
        k = re.sub(r"<[^>]+>", "", k).strip()
        v = re.sub(r"<[^>]+>", "", v).strip()
        if not k or k in row:
            continue
        if v in ("<Null>", "&lt;Null&gt;", ""):
            v = ""
        row[k] = v
    return row


def parse_coords(text: str) -> list:
    coords = []
    for token in (text or "").split():
        parts = token.split(",")
        if len(parts) >= 2:
            lng, lat = float(parts[0]), float(parts[1])
            coords.append([lng, lat])
    return coords


def main():
    with zipfile.ZipFile(KMZ) as z:
        kml = z.read("doc.kml").decode("utf-8")
    root = ET.fromstring(kml.encode("utf-8"))

    features = []
    for pm in root.findall(".//k:Placemark", NS):
        name_el = pm.find("k:name", NS)
        street = (name_el.text or "").strip()
        desc_el = pm.find("k:description", NS)
        attrs = parse_description(desc_el.text if desc_el is not None else "")
        line = pm.find(".//k:LineString/k:coordinates", NS)
        if line is None or not line.text:
            continue
        coords = parse_coords(line.text)
        if len(coords) < 2:
            continue

        direction = attrs.get("اتجاه المقطع", "")
        props = {
            "name": street,
            "street": street,
            "segment_code": attrs.get("رمز المقطع", ""),
            "from_street": attrs.get("من الشارع", ""),
            "to_street": attrs.get("الى الشارع", ""),
            "main_street_code": attrs.get("رمز الشارع الرئيسي", ""),
            "region_no": attrs.get("رقم المنطقة", ""),
            "direction": direction,
            "direction_label": DIR_LABELS.get(direction, direction),
            "municipality": attrs.get("اسم البلدية باللغة العربية", ""),
            "district": attrs.get("اسم الحي باللغة العربية", ""),
            "sub_district": attrs.get("اسم الحي الفرعي باللغة العربية", ""),
            "length_m": attrs.get("طول المقطع", ""),
            "width_m": attrs.get("عرض المقطع", ""),
            "area_m2": attrs.get("AREA_OF_SECTION", ""),
            "street_type": attrs.get("Street_Type", ""),
            "color": STREET_COLORS.get(street, "#fbbf24"),
        }
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": props,
        })

    geojson = {"type": "FeatureCollection", "features": features}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(features)} features to {OUT}")


if __name__ == "__main__":
    main()
