from rest_framework import serializers
from .models import Bridge, Defect, DefectImage, Road, RoadDefect, RoadDefectImage, Lighting, Zone, Contract


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
    color = serializers.CharField(read_only=True)

    class Meta:
        model = RoadDefect
        fields = [
            "id", "road", "title", "status", "status_display",
            "direction", "direction_display",
            "observation", "description",
            "lat", "lng", "color", "images"
        ]


class RoadSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)
    color = serializers.CharField(read_only=True)
    defects = RoadDefectSerializer(many=True, read_only=True)
    defects_count = serializers.SerializerMethodField()
    untreated_count = serializers.SerializerMethodField()

    class Meta:
        model = Road
        fields = [
            "id", "segment", "status", "status_display", "direction", "direction_display",
            "color", "created_at", "defects", "defects_count", "untreated_count"
        ]

    def get_defects_count(self, obj):
        return obj.defects.count()

    def get_untreated_count(self, obj):
        return obj.defects.filter(treatment_type="untreated").count()


class LightingSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    color = serializers.CharField(read_only=True)

    class Meta:
        model = Lighting
        fields = ["id", "number", "type", "type_display", "lat", "lng", "color", "created_at"]


class ContractSerializer(serializers.ModelSerializer):
    # To return full zone details if needed, but usually we just want IDs on write and maybe nested on read.
    # We will use primary key related field for write, and override to_representation if needed.
    zones = serializers.PrimaryKeyRelatedField(many=True, queryset=Zone.objects.all())

    class Meta:
        model = Contract
        fields = ["id", "project_name", "value", "department", "status", "zones", "created_at"]


class ZoneSerializer(serializers.ModelSerializer):
    contracts = ContractSerializer(many=True, read_only=True)

    class Meta:
        model = Zone
        fields = ["id", "name", "color", "geom", "contracts", "created_at"]

