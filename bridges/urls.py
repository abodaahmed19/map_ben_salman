from rest_framework.routers import DefaultRouter
from .views import BridgeViewSet, RoadViewSet, DefectViewSet, DefectImageViewSet, RoadDefectViewSet, RoadDefectImageViewSet, LightingViewSet, ZoneViewSet, ContractViewSet

router = DefaultRouter()
router.register("bridges", BridgeViewSet)
router.register("roads", RoadViewSet)
router.register("defects", DefectViewSet)
router.register("images", DefectImageViewSet)
router.register("road-defects", RoadDefectViewSet)
router.register("road-images", RoadDefectImageViewSet)
router.register("lightings", LightingViewSet)
router.register("zones", ZoneViewSet)
router.register("contracts", ContractViewSet)

urlpatterns = router.urls
