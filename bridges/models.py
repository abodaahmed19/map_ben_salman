from django.db import models


class Bridge(models.Model):
    STATUS = [
        ("critical", "حرج"),
        ("operational", "ضعيف"),
        ("maintenance", "مقبول"),
        ("good", "جيد"),
    ]
    STATUS_COLORS = {
        "critical": "rgb(220, 38, 38)",
        "operational": "rgb(234, 88, 12)",
        "maintenance": "rgb(217, 119, 6)",
        "good": "rgb(22, 163, 74)",
    }

    name = models.CharField("اسم الجسر", max_length=200)
    status = models.CharField("الحالة", max_length=20, choices=STATUS, default="operational")
    # موقع الجسر على الخريطة (نقطة بإحداثيات)
    lat = models.FloatField("خط العرض", default=21.4275)
    lng = models.FloatField("خط الطول", default=39.8235)
    description = models.TextField("الوصف", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "جسر"
        verbose_name_plural = "الجسور"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def color(self):
        return self.STATUS_COLORS.get(self.status, "#3c7a5a")


class Defect(models.Model):
    DSTATUS = [
        ("open", "مفتوح"),
        ("in_progress", "جاري المعالجة"),
        ("resolved", "منتهى"),
    ]

    bridge = models.ForeignKey(Bridge, related_name="defects", on_delete=models.CASCADE, verbose_name="الجسر")
    title = models.CharField("اسم العيب", max_length=200)
    status = models.CharField("الحالة", max_length=15, choices=DSTATUS, default="open")
    description = models.TextField("الوصف", blank=True)
    length_m = models.FloatField("الطول (م)", default=0)
    width_m = models.FloatField("العرض (م)", default=0)
    area_m2 = models.FloatField("المساحة (م²)", default=0)
    count = models.PositiveIntegerField("العدد", default=0)

    class Meta:
        verbose_name = "عيب"
        verbose_name_plural = "العيوب"

    def __str__(self):
        return f"{self.title} ({self.bridge.name})"


class DefectImage(models.Model):
    defect = models.ForeignKey(Defect, related_name="images", on_delete=models.CASCADE, verbose_name="العيب")
    image = models.ImageField("الصورة", upload_to="defects/")
    caption = models.CharField("وصف الصورة", max_length=200, blank=True)

    class Meta:
        verbose_name = "صورة عيب"
        verbose_name_plural = "صور العيوب"

    def __str__(self):
        return self.caption or f"صورة #{self.pk}"


class Road(models.Model):
    STATUS = [
        ("critical", "حرج"),
        ("medium", "متوسط"),
        ("low", "منخفض"),
    ]
    DIRECTION = [
        ("mecca", "مكة"),
        ("jeddah", "جدة"),
    ]
    STATUS_COLORS = {
        "critical": "rgb(220, 38, 38)",
        "medium": "rgb(234, 88, 12)",
        "low": "rgb(34, 197, 94)",
    }

    segment = models.CharField("المقطع", max_length=200)
    status = models.CharField("الحالة", max_length=20, choices=STATUS, default="medium")
    direction = models.CharField("الاتجاه", max_length=20, choices=DIRECTION, default="mecca")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "طريق"
        verbose_name_plural = "الطرق"

    def __str__(self):
        return f"{self.segment} ({self.get_status_display()})"

    @property
    def color(self):
        return self.STATUS_COLORS.get(self.status, "#3c7a5a")


class RoadDefect(models.Model):
    STATUS = [
        ("critical", "حرج"),
        ("medium", "متوسط"),
        ("low", "منخفض"),
    ]
    TREATMENT = [
        ("treated", "معالج"),
        ("untreated", "غير معالج"),
    ]
    DIRECTION = [
        ("mecca", "مكة"),
        ("jeddah", "جدة"),
    ]

    STATUS_COLORS = {
        "critical": "rgb(220, 38, 38)",
        "medium": "rgb(234, 88, 12)",
        "low": "rgb(34, 197, 94)",
    }

    road = models.ForeignKey(Road, related_name="defects", on_delete=models.CASCADE, verbose_name="الطريق")
    title = models.CharField("اسم/عنوان الحالة", max_length=200, blank=True)
    status = models.CharField("الحالة", max_length=20, choices=STATUS, default="medium")
    direction = models.CharField("الاتجاه", max_length=20, choices=DIRECTION, default="mecca")
    observation = models.CharField("الملاحظة", max_length=255, blank=True, help_text="اسفلت - أصول جانبي الطريق")
    description = models.TextField("الوصف", blank=True)
    treatment_type = models.CharField("نوع المعالجة", max_length=20, choices=TREATMENT, default="untreated")
    # موقع الحالة على الخريطة (كل حالة ماركر مستقل)
    lat = models.FloatField("خط العرض", default=21.38866)
    lng = models.FloatField("خط الطول", default=39.42683)

    class Meta:
        verbose_name = "حالة طريق"
        verbose_name_plural = "حالات الطرق"

    def __str__(self):
        return f"{self.title or 'حالة'} ({self.road.segment})"

    @property
    def color(self):
        return self.STATUS_COLORS.get(self.status, "#3c7a5a")


class RoadDefectImage(models.Model):
    defect = models.ForeignKey(RoadDefect, related_name="images", on_delete=models.CASCADE, verbose_name="الحالة")
    image = models.ImageField("الصورة", upload_to="road_defects/")
    caption = models.CharField("وصف الصورة", max_length=200, blank=True)

    class Meta:
        verbose_name = "صورة حالة طريق"
        verbose_name_plural = "صور حالات الطرق"

    def __str__(self):
        return self.caption or f"صورة #{self.pk}"


class Lighting(models.Model):
    TYPE_CHOICES = [
        ("pole", "عمود"),
        ("tower", "برج"),
    ]

    number = models.CharField("رقم العمود/البرج", max_length=100)
    type = models.CharField("النوع", max_length=20, choices=TYPE_CHOICES, default="pole")
    lat = models.FloatField("خط العرض", default=21.4275)
    lng = models.FloatField("خط الطول", default=39.8235)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "إنارة"
        verbose_name_plural = "الإنارة"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_type_display()} - {self.number}"

    @property
    def color(self):
        return "rgb(156, 163, 175)"


class Zone(models.Model):
    name = models.CharField("اسم النطاق", max_length=200)
    color = models.CharField("لون الخط", max_length=20, default="#3b82f6")
    # Store polyline coordinates as JSON, e.g. [[lat, lng], [lat, lng], ...]
    geom = models.JSONField("الإحداثيات", default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "نطاق"
        verbose_name_plural = "النطاقات"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Contract(models.Model):
    project_name = models.CharField("اسم المشروع", max_length=300)
    value = models.FloatField("قيمة صرف العقد", default=0.0)
    department = models.CharField("الادارة", max_length=200, blank=True)
    status = models.CharField("حالة العقد", max_length=100, blank=True, null=True)
    zones = models.ManyToManyField(Zone, related_name="contracts", verbose_name="النطاقات")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "عقد"
        verbose_name_plural = "العقود"
        ordering = ["-created_at"]

    def __str__(self):
        return self.project_name
