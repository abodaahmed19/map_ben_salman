from rest_framework.routers import DefaultRouter
from .views import BridgeViewSet, DefectViewSet, DefectImageViewSet

router = DefaultRouter()
router.register("bridges", BridgeViewSet)
router.register("defects", DefectViewSet)
router.register("images", DefectImageViewSet)

urlpatterns = router.urls
