from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Bridge, Defect, DefectImage, Road, RoadDefect, RoadDefectImage, Lighting, Zone, Contract
from .serializers import BridgeSerializer, DefectSerializer, DefectImageSerializer, RoadSerializer, RoadDefectSerializer, RoadDefectImageSerializer, LightingSerializer, ZoneSerializer, ContractSerializer


class BridgeViewSet(viewsets.ModelViewSet):
    queryset = Bridge.objects.prefetch_related("defects__images").all()
    serializer_class = BridgeSerializer


class RoadViewSet(viewsets.ModelViewSet):
    queryset = Road.objects.prefetch_related("defects__images").all()
    serializer_class = RoadSerializer


class DefectViewSet(viewsets.ModelViewSet):
    queryset = Defect.objects.prefetch_related("images").all()
    serializer_class = DefectSerializer

    @action(detail=True, methods=["post"], url_path="upload")
    def upload(self, request, pk=None):
        """رفع صورة واحدة أو أكثر لعيب محدد."""
        defect = self.get_object()
        files = request.FILES.getlist("image") or request.FILES.getlist("images")
        captions = request.data.getlist("caption") if hasattr(request.data, "getlist") else []
        created = []
        for i, f in enumerate(files):
            cap = captions[i] if i < len(captions) else ""
            img = DefectImage.objects.create(defect=defect, image=f, caption=cap)
            created.append(DefectImageSerializer(img, context={"request": request}).data)
        return Response(created, status=status.HTTP_201_CREATED)


class DefectImageViewSet(viewsets.ModelViewSet):
    queryset = DefectImage.objects.all()
    serializer_class = DefectImageSerializer


class RoadDefectViewSet(viewsets.ModelViewSet):
    queryset = RoadDefect.objects.prefetch_related("images").all()
    serializer_class = RoadDefectSerializer

    @action(detail=True, methods=["post"], url_path="upload")
    def upload(self, request, pk=None):
        """رفع صورة واحدة أو أكثر لحالة طريق محددة."""
        defect = self.get_object()
        files = request.FILES.getlist("image") or request.FILES.getlist("images")
        captions = request.data.getlist("caption") if hasattr(request.data, "getlist") else []
        created = []
        for i, f in enumerate(files):
            cap = captions[i] if i < len(captions) else ""
            img = RoadDefectImage.objects.create(defect=defect, image=f, caption=cap)
            created.append(RoadDefectImageSerializer(img, context={"request": request}).data)
        return Response(created, status=status.HTTP_201_CREATED)


class RoadDefectImageViewSet(viewsets.ModelViewSet):
    queryset = RoadDefectImage.objects.all()
    serializer_class = RoadDefectImageSerializer


class LightingViewSet(viewsets.ModelViewSet):
    queryset = Lighting.objects.all()
    serializer_class = LightingSerializer


class ZoneViewSet(viewsets.ModelViewSet):
    queryset = Zone.objects.prefetch_related("contracts").all()
    serializer_class = ZoneSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        cat = self.request.query_params.get("category")
        if cat:
            qs = qs.filter(category=cat)
        return qs


class ContractViewSet(viewsets.ModelViewSet):
    queryset = Contract.objects.prefetch_related("zones").all()
    serializer_class = ContractSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        cat = self.request.query_params.get("category")
        if cat:
            qs = qs.filter(category=cat)
        return qs
