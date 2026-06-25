from rest_framework import serializers
from .models import Bridge, Defect, DefectImage


class DefectImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefectImage
        fields = ["id", "image", "caption"]


class DefectSerializer(serializers.ModelSerializer):
    images = DefectImageSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Defect
        fields = [
            "id", "bridge", "title", "status", "status_display", "description",
            "length_m", "width_m", "area_m2", "count", "images",
        ]


class BridgeSerializer(serializers.ModelSerializer):
    defects = DefectSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    color = serializers.CharField(read_only=True)
    defects_count = serializers.SerializerMethodField()
    open_count = serializers.SerializerMethodField()

    class Meta:
        model = Bridge
        fields = [
            "id", "name", "status", "status_display", "color",
            "lat", "lng", "defects", "defects_count", "open_count",
        ]

    def get_defects_count(self, obj):
        return obj.defects.count()

    def get_open_count(self, obj):
        return obj.defects.exclude(status="resolved").count()
