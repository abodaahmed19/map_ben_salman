from rest_framework import serializers
from .models import Bridge, Defect, DefectImage, Road, RoadDefect, RoadDefectImage


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
            "description", "lat", "lng", "defects", "defects_count", "open_count",
        ]

    def get_defects_count(self, obj):
        return obj.defects.count()

    def get_open_count(self, obj):
        return obj.defects.exclude(status="resolved").count()


class RoadDefectImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoadDefectImage
        fields = ["id", "image", "caption"]


class RoadDefectSerializer(serializers.ModelSerializer):
    images = RoadDefectImageSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)
    treatment_type_display = serializers.CharField(source="get_treatment_type_display", read_only=True)

    class Meta:
        model = RoadDefect
        fields = [
            "id", "road", "title", "status", "status_display", "direction", "direction_display",
            "observation", "description", "treatment_type", "treatment_type_display", "images"
        ]


class RoadSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    color = serializers.CharField(read_only=True)
    defects = RoadDefectSerializer(many=True, read_only=True)
    defects_count = serializers.SerializerMethodField()
    untreated_count = serializers.SerializerMethodField()

    class Meta:
        model = Road
        fields = [
            "id", "segment", "status", "status_display", "lat", "lng", "color", "created_at",
            "defects", "defects_count", "untreated_count"
        ]

    def get_defects_count(self, obj):
        return obj.defects.count()

    def get_untreated_count(self, obj):
        return obj.defects.filter(treatment_type="untreated").count()

