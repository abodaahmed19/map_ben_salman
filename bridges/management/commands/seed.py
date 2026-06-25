"""بيانات تجريبية لمحور طريق محمد بن سلمان + صور مولّدة + مستخدم admin."""
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from PIL import Image, ImageDraw
from bridges.models import Bridge, Defect, DefectImage

STATUS_RGB = {"operational": (60, 122, 90), "maintenance": (150, 120, 54), "critical": (179, 70, 58)}


def make_image(caption, status):
    """صورة تجريبية ملوّنة بهوية الأمانة."""
    w, h = 480, 340
    img = Image.new("RGB", (w, h), (24, 48, 40))
    d = ImageDraw.Draw(img)
    c = STATUS_RGB.get(status, (60, 122, 90))
    for i in range(0, h, 18):
        d.line([(0, i), (w, i - 60)], fill=(c[0] // 3 + 24, c[1] // 3 + 40, c[2] // 3 + 36), width=2)
    d.rectangle([20, 20, w - 20, h - 20], outline=c, width=4)
    d.ellipse([w // 2 - 34, h // 2 - 50, w // 2 + 34, h // 2 + 18], outline=(220, 220, 210), width=4)
    d.rectangle([w // 2 - 50, h // 2 - 34, w // 2 + 50, h // 2 + 30], outline=(220, 220, 210), width=4)
    d.text((28, h - 40), caption, fill=(230, 230, 222))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return ContentFile(buf.getvalue())


DATA = [
    {
        "name": "جسر الملك عبدالعزيز", "status": "operational",
        "lat": 21.4308, "lng": 39.8214,
        "defects": [
            {"title": "تشقق طولي في سطح الأسفلت", "status": "open",
             "description": "تشقق طولي على المسار الأيمن يحتاج سفلتة موضعية قبل موسم الأمطار.",
             "length_m": 12, "width_m": 0.3, "area_m2": 3.6, "count": 1,
             "imgs": ["تشقق طولي - مسار أيمن", "قياس عرض الشق"]},
            {"title": "تآكل فاصل التمدد", "status": "resolved",
             "description": "تآكل بسيط في فاصل التمدد المعدني، تمت المعالجة وإعادة الإحكام.",
             "length_m": 8, "width_m": 0.2, "area_m2": 1.6, "count": 2,
             "imgs": ["فاصل التمدد", "بعد المعالجة"]},
        ],
    },
    {
        "name": "جسر العزيزية المعلّق", "status": "maintenance",
        "lat": 21.4241, "lng": 39.8325,
        "defects": [
            {"title": "هبوط في الكتف الترابي", "status": "in_progress",
             "description": "هبوط ملحوظ في الكتف الترابي عند الدعامة الجنوبية بمقدار 8 سم، أعمال المعالجة جارية.",
             "length_m": 5, "width_m": 2.5, "area_m2": 12.5, "count": 1,
             "imgs": ["هبوط الكتف الترابي", "الدعامة الجنوبية", "أعمال المعالجة"]},
        ],
    },
    {
        "name": "جسر مشاة النسيم", "status": "critical",
        "lat": 21.4203, "lng": 39.8175,
        "defects": [
            {"title": "صدأ في الحاجز الجانبي", "status": "open",
             "description": "صدأ متقدم في الحاجز المعدني الجانبي يهدد سلامة المشاة ويتطلب استبدالًا فوريًا.",
             "length_m": 18, "width_m": 1.1, "area_m2": 19.8, "count": 6,
             "imgs": ["صدأ الحاجز الجانبي", "القطاع المتضرر"]},
        ],
    },
]


class Command(BaseCommand):
    help = "تعبئة بيانات تجريبية وإنشاء مستخدم admin"

    def handle(self, *args, **opts):
        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "admin12345")
            self.stdout.write(self.style.SUCCESS("أُنشئ مستخدم admin / admin12345"))

        Bridge.objects.all().delete()
        for b in DATA:
            bridge = Bridge.objects.create(name=b["name"], status=b["status"], lat=b["lat"], lng=b["lng"])
            for d in b["defects"]:
                defect = Defect.objects.create(
                    bridge=bridge, title=d["title"], status=d["status"], description=d["description"],
                    length_m=d["length_m"], width_m=d["width_m"], area_m2=d["area_m2"], count=d["count"],
                )
                for n, cap in enumerate(d["imgs"]):
                    di = DefectImage(defect=defect, caption=cap)
                    di.image.save(f"seed_{defect.id}_{n}.jpg", make_image(cap, b["status"]), save=True)
        self.stdout.write(self.style.SUCCESS(f"تم إنشاء {Bridge.objects.count()} جسور بنجاح"))
