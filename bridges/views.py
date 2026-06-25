from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Bridge, Defect, DefectImage
from .serializers import BridgeSerializer, DefectSerializer, DefectImageSerializer


class BridgeViewSet(viewsets.ModelViewSet):
    queryset = Bridge.objects.prefetch_related("defects__images").all()
    serializer_class = BridgeSerializer


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
