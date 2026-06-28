"""تعبئة إحداثيات حالات الطرق الحالية من موقع الطريق الأب (بدون فقد أي بيانات)."""
from django.db import migrations


def seed_coords(apps, schema_editor):
    RoadDefect = apps.get_model("bridges", "RoadDefect")
    for d in RoadDefect.objects.select_related("road").all():
        if d.road_id:
            d.lat = d.road.lat
            d.lng = d.road.lng
            d.save(update_fields=["lat", "lng"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("bridges", "0007_roaddefect_lat_roaddefect_lng"),
    ]

    operations = [
        migrations.RunPython(seed_coords, noop),
    ]
