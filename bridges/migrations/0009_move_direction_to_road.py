"""نقل (الاتجاه) من حالة الطريق إلى المقطع، وإزالة إحداثيات المقطع — مع الحفاظ على القيم."""
from django.db import migrations, models


def copy_direction_up(apps, schema_editor):
    """ينسخ اتجاه أول حالة في كل مقطع إلى المقطع نفسه قبل حذف الحقل من الحالات."""
    Road = apps.get_model("bridges", "Road")
    for road in Road.objects.all():
        first = road.defects.first()
        if first is not None:
            road.direction = getattr(first, "direction", "mecca") or "mecca"
            road.save(update_fields=["direction"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("bridges", "0008_roaddefect_seed_coords"),
    ]

    operations = [
        migrations.AddField(
            model_name="road",
            name="direction",
            field=models.CharField(
                choices=[("mecca", "مكة"), ("jeddah", "جدة")],
                default="mecca", max_length=20, verbose_name="الاتجاه",
            ),
        ),
        migrations.RunPython(copy_direction_up, noop),
        migrations.RemoveField(model_name="roaddefect", name="direction"),
        migrations.RemoveField(model_name="road", name="lat"),
        migrations.RemoveField(model_name="road", name="lng"),
    ]
