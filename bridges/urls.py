from rest_framework.routers import DefaultRouter
from .views import BridgeViewSet, RoadViewSet, DefectViewSet, DefectImageViewSet, RoadDefectViewSet, RoadDefectImageViewSet

router = DefaultRouter()
router.register("bridges", BridgeViewSet)
router.register("roads", RoadViewSet)
router.register("defects", DefectViewSet)
router.register("images", DefectImageViewSet)
router.register("road-defects", RoadDefectViewSet)
router.register("road-images", RoadDefectImageViewSet)

urlpatterns = router.urls
