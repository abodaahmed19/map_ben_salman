import os, sys, django
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from bridges.models import Contract, Zone
from pathlib import Path

out = []
out.append("ZONES current:")
for z in Zone.objects.filter(category="current"):
    out.append(f"  {z.id} | {z.name} | contracts: {z.contracts.count()}")
out.append("ZONES new2028:")
for z in Zone.objects.filter(category="new2028"):
    out.append(f"  {z.id} | {z.name} | contracts: {z.contracts.count()}")
out.append(f"CONTRACTS current: {Contract.objects.filter(category='current').count()}")
out.append(f"CONTRACTS new2028: {Contract.objects.filter(category='new2028').count()}")
for c in Contract.objects.all().order_by("category", "order", "id"):
    zs = list(c.zones.values_list("name", flat=True))
    out.append(f"{c.id} | {c.category} | {c.value} | {c.project_name} | zones: {zs}")

Path(__file__).resolve().parent.joinpath("db_contracts_report.txt").write_text("\n".join(out), encoding="utf-8")
print("done")
