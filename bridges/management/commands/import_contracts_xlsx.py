"""تحديث عقود المحور من ملف Excel (الاسم والقيمة فقط).

python manage.py import_contracts_xlsx --excel "path.xlsx"
python manage.py import_contracts_xlsx --excel "path.xlsx" --dry-run
"""
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from bridges.models import Contract, Zone

ROOT = Path(__file__).resolve().parents[3]

SECTION_MARKERS = {
    "current contracts": "current",
    "contracts in progress": "in_progress",
    "planned contracts": "planned",
    "عقود الصيانة البديلة لمحور الأمير محمد بن سلمان من عام 2028": "planned",
    "عقود التأهيل المطلوبة لمحور الأمير محمد بن سلمان من عام 2028": "planned",
}
CITY_MARKERS = {"mecca": "mecca", "jeddah": "jeddah"}
SKIP_NAMES = {
    "cost item",
    "contract value (sar)",
    "mecca",
    "jeddah",
}


def norm_name(value: str) -> str:
    s = unicodedata.normalize("NFKC", str(value or "")).strip()
    s = s.replace("*", "")
    s = re.sub(r"\s+", " ", s)
    s = s.replace("شغيل", "تشغيل")
    s = re.sub(r"\bالطرق\b|\bالطريق\b", "طريق", s)
    s = s.replace("مشرو ع", "مشروع")
    return s.casefold()


def parse_value(raw) -> float | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def guess_zone_for_current(name: str, section: str, city: str, zones: dict[str, Zone]) -> Zone | None:
    if section == "in_progress":
        return zones.get("نطاق من جسر الزايدي الي جسر بحرة")

    n = norm_name(name)
    if city == "jeddah":
        return None

    if any(k in n for k in ("محور", "بوابة مكة", "بحرة", "الزايدي", "نظافة محاور", "محاور الأمير")):
        return zones.get("نطاق من جسر الزايدي الي جسر بحرة")
    if any(k in n for k in ("مستلم", "وزارة النقل", "السلامة المرورية", "الدائري الثالث")):
        return zones.get("نطاق من الدائري الثالث الي جسر الزايدي")
    if any(k in n for k in ("الدائري الأول", "الدائري الاول", "المركزية", "وسط مكة", "بمكة المكرمة")):
        return zones.get("نطاق من الدائري الاول الي الدائري الثالث")
    return zones.get("نطاق من الدائري الاول الي الدائري الثالث")


def group_num(name: str) -> str | None:
    m = re.search(r"المجموعة\s*(\S+)", name)
    return m.group(1).casefold() if m else None


def should_import_row(item: dict) -> bool:
    if item["city"] != "jeddah":
        return True
    n = norm_name(item["name"])
    return "محور" in n or "الأمير محمد بن سلمان" in n


def best_match(name: str, contracts: list[Contract], used_ids: set[int]) -> Contract | None:
    target = norm_name(name)
    for c in contracts:
        if c.id not in used_ids and norm_name(c.project_name) == target:
            return c

    tg = group_num(name)
    best, score = None, 0.0
    for c in contracts:
        if c.id in used_ids:
            continue
        if tg and group_num(c.project_name) != tg:
            continue
        cn = norm_name(c.project_name)
        s = SequenceMatcher(None, target, cn).ratio()
        if s > score:
            best, score = c, s
    return best if score >= 0.9 else None


def parse_rows(excel_path: str) -> list[dict]:
    df = pd.read_excel(excel_path, sheet_name=0, header=None)
    city = "mecca"
    section = "current"
    rows = []

    for idx, row in df.iterrows():
        raw_name = row.iloc[0]
        raw_value = row.iloc[1] if len(row) > 1 else None
        if raw_name is None or (isinstance(raw_name, float) and pd.isna(raw_name)):
            continue

        name = str(raw_name).strip()
        key = name.casefold()
        if key in CITY_MARKERS:
            city = CITY_MARKERS[key]
            continue
        if key in SECTION_MARKERS:
            section = SECTION_MARKERS[key]
            continue
        if key in SKIP_NAMES:
            continue

        value = parse_value(raw_value)
        if value is None:
            continue

        category = "new2028" if section == "planned" else "current"
        rows.append({
            "row": int(idx),
            "name": name,
            "value": value,
            "category": category,
            "city": city,
            "section": section,
        })
    return rows


class Command(BaseCommand):
    help = "تحديث/إنشاء عقود الحالية و2028 من ملف Excel"

    def add_arguments(self, parser):
        parser.add_argument("--excel", required=True, help="مسار ملف Excel")
        parser.add_argument("--dry-run", action="store_true", help="معاينة بدون حفظ")

    def handle(self, *args, **options):
        excel_path = options["excel"]
        dry_run = options["dry_run"]

        try:
            parsed = parse_rows(excel_path)
        except Exception as exc:
            raise CommandError(f"تعذر قراءة الملف: {exc}") from exc

        zones = {z.name: z for z in Zone.objects.all()}
        new_zone = zones.get("من الدائري الاول الي جسر بحره")
        if not new_zone:
            raise CommandError("نطاق العقود الجديدة 2028 غير موجود في قاعدة البيانات")

        existing = {
            "current": list(Contract.objects.filter(category="current")),
            "new2028": list(Contract.objects.filter(category="new2028")),
        }
        used_ids: set[int] = set()
        created = updated = skipped = 0
        report = []

        def run():
            nonlocal created, updated, skipped
            order_counters = {"current": 0, "new2028": 0}
            for item in parsed:
                if not should_import_row(item):
                    continue
                cat = item["category"]
                order_counters[cat] += 1
                match = best_match(item["name"], existing[cat], used_ids)

                if match:
                    used_ids.add(match.id)
                    old_name, old_value = match.project_name, match.value
                    changed = False
                    if match.project_name != item["name"]:
                        match.project_name = item["name"]
                        changed = True
                    if float(match.value or 0) != float(item["value"]):
                        match.value = item["value"]
                        changed = True
                    if match.order != order_counters[cat]:
                        match.order = order_counters[cat]
                        changed = True
                    if changed:
                        match.save(update_fields=["project_name", "value", "order"])
                        updated += 1
                        report.append(f"UPDATE [{cat}] {old_name} -> value {old_value} => {item['value']}")
                    else:
                        skipped += 1
                    continue

                zone = new_zone if cat == "new2028" else guess_zone_for_current(
                    item["name"], item["section"], item["city"], zones
                )
                contract = Contract.objects.create(
                    project_name=item["name"],
                    value=item["value"],
                    category=cat,
                    order=order_counters[cat],
                )
                if zone:
                    contract.zones.set([zone])
                existing[cat].append(contract)
                created += 1
                zone_name = zone.name if zone else "بدون نطاق"
                report.append(f"CREATE [{cat}] {item['name']} = {item['value']} | zone: {zone_name}")

        if dry_run:
            with transaction.atomic():
                run()
                transaction.set_rollback(True)
        else:
            run()

        mode = "preview" if dry_run else "done"
        summary = f"{mode}: created={created}, updated={updated}, unchanged={skipped}, rows={len(parsed)}"
        report_path = ROOT / "scripts" / "import_contracts_report.txt"
        report_path.write_text(summary + "\n" + "\n".join(report), encoding="utf-8")
        self.stdout.write(summary)
        self.stdout.write(f"Report: {report_path}")
