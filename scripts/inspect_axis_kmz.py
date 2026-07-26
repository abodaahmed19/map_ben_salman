import json
import re
import zipfile
from html import unescape
from pathlib import Path

KMZ = Path(r"C:\Users\Eng Abdelatif\Downloads\محور الامير محمد بن سلمان.kmz")
OUT = Path(__file__).resolve().parent / "kmz_axis_roads_inspect.txt"

with zipfile.ZipFile(KMZ) as z:
    kml = z.read([n for n in z.namelist() if n.lower().endswith(".kml")][0]).decode("utf-8", errors="replace")

lines = [
    f"size={len(kml)}",
    f"LineString={len(re.findall(r'<LineString', kml, re.I))}",
    f"Point={len(re.findall(r'<Point', kml, re.I))}",
    f"Placemarks={len(re.findall(r'<Placemark', kml, re.I))}",
]
names = sorted({re.sub(r"<[^>]+>", "", m).strip() for m in re.findall(r"<name>(.*?)</name>", kml, re.S)})
lines.append(f"unique names ({len(names)}): {json.dumps(names[:25], ensure_ascii=False)}")
for i, block in enumerate(re.findall(r"<Placemark\b[^>]*>.*?</Placemark>", kml, re.S | re.I)[:5]):
    nm = re.search(r"<name>(.*?)</name>", block, re.S | re.I)
    coords = re.search(r"<coordinates>(.*?)</coordinates>", block, re.S | re.I)
    g = "LineString" if re.search(r"<LineString", block, re.I) else "Point" if re.search(r"<Point", block, re.I) else "other"
    name = plain = unescape(re.sub(r"<[^>]+>", "", nm.group(1)).strip()) if nm else ""
    pts = len(coords.group(1).split()) if coords else 0
    lines.append(f"sample{i}: {g} name={name[:80]} pts={pts}")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(OUT)
