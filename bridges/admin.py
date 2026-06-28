from django.contrib import admin
from .models import Bridge, Defect, DefectImage, Road


class DefectImageInline(admin.TabularInline):
    model = DefectImage
    extra = 1


class DefectInline(admin.StackedInline):
    model = Defect
    extra = 0
    show_change_link = True


@admin.register(Bridge)
class BridgeAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "lat", "lng")
    list_filter = ("status",)
    search_fields = ("name",)
    inlines = [DefectInline]


@admin.register(Road)
class RoadAdmin(admin.ModelAdmin):
    list_display = ("segment", "status", "direction", "created_at")
    list_filter = ("status", "direction")
    search_fields = ("segment",)
    readonly_fields = ("created_at",)
    fieldsets = (
        ("معلومات الطريق", {
            "fields": ("segment", "status", "direction")
        }),
        ("المعلومات", {
            "fields": ("created_at",),
            "classes": ("collapse",)
        }),
    )


@admin.register(Defect)
class DefectAdmin(admin.ModelAdmin):
    list_display = ("title", "bridge", "status", "length_m", "width_m", "area_m2", "count")
    list_filter = ("status", "bridge")
    inlines = [DefectImageInline]


admin.site.site_header = "محور طريق محمد بن سلمان — لوحة الإدارة"
admin.site.site_title = "محور طريق محمد بن سلمان"
admin.site.index_title = "إدارة أصول النقل والبنية التحتية"
