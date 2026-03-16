from rest_framework.routers import DefaultRouter

from .views import OptimizedBookViewSet, UnoptimizedBookViewSet

router = DefaultRouter()
router.register(
    r"books/unoptimized", UnoptimizedBookViewSet, basename="unoptimized-books"
)
router.register(r"books/optimized", OptimizedBookViewSet, basename="optimized-books")

urlpatterns = router.urls
