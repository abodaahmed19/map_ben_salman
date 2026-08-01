"""Count placemarks per folder using ElementTree."""
from __future__ import annotations

import json
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

PATH = Path(r"C:\Users\Eng Abdelatif\Downloads\Prince Mohammed Bin Salman Road.kmz")
OUT = Path(__file__).resolve().parent / "roads_kmz_folders.json"
NS = {"k": "http://www.opengis.net/kml/2.2"}


def geom_type(pm: ET.Element) -> str:
    if pm.find(".//k:Point", NS) is not None:
        return "Point"
    if pm.find(".//k:LineString", NS) is not None:
        return "LineString"
    if pm.find(".//k:Polygon", NS) is not None:
        return "Polygon"
    return "other"


def folder_report(folder: ET.Element, path: list[str]) -> list[dict]:
    name_el = folder.find("k:name", NS)
    name = (name_el.text or "").strip() if name_el is not None else "بدون اسم"
    current = path + [name]

    placemarks = folder.findall("k:Placemark", NS)
    geoms = Counter(geom_type(pm) for pm in placemarks)
    names = []
    for pm in placemarks:
        nm = pm.find("k:name", NS)
        names.append((nm.text or "").strip() if nm is not None else "")

    reports = [
        {
            "path": " / ".join(current),
            "placemark_count": len(placemarks),
            "geometry_types": dict(geoms),
            "name_samples": [n for n in names[:20] if n],
        }
    ]

    for child in folder.findall("k:Folder", NS):
        reports.extend(folder_report(child, current))

    return reports


def main() -> None:
    with zipfile.ZipFile(PATH) as z:
        kml = z.read(next(n for n in z.namelist() if n.lower().endswith(".kml")))
    root = ET.fromstring(kml)
    doc = root.find(".//k:Document", NS)
    reports = []
    if doc is not None:
        for folder in doc.findall("k:Folder", NS):
            reports.extend(folder_report(folder, []))

    OUT.write_text(
        json.dumps({"folders": reports, "folder_paths": [r["path"] for r in reports]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for r in reports:
        print(r["path"], r["placemark_count"], r["geometry_types"])


if __name__ == "__main__":
    main()
