from rest_framework.routers import DefaultRouter

from .views import OptimizedUserViewSet, UnoptimizedUserViewSet

router = DefaultRouter()
router.register(
    r"users/unoptimized", UnoptimizedUserViewSet, basename="unoptimized-users"
)
router.register(r"users/optimized", OptimizedUserViewSet, basename="optimized-users")

urlpatterns = router.urls
