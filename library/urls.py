from rest_framework.routers import DefaultRouter

from .views import (
    OptimizedBorrowRecordViewSet,
    OptimizedReadingListViewSet,
    OptimizedReviewViewSet,
    UnoptimizedBorrowRecordViewSet,
    UnoptimizedReadingListViewSet,
    UnoptimizedReviewViewSet,
)

router = DefaultRouter()
router.register(
    r"reviews/unoptimized", UnoptimizedReviewViewSet, basename="unoptimized-reviews"
)
router.register(
    r"reviews/optimized", OptimizedReviewViewSet, basename="optimized-reviews"
)
router.register(
    r"reading-lists/unoptimized",
    UnoptimizedReadingListViewSet,
    basename="unoptimized-reading-lists",
)
router.register(
    r"reading-lists/optimized",
    OptimizedReadingListViewSet,
    basename="optimized-reading-lists",
)
router.register(
    r"borrow-records/unoptimized",
    UnoptimizedBorrowRecordViewSet,
    basename="unoptimized-borrow-records",
)
router.register(
    r"borrow-records/optimized",
    OptimizedBorrowRecordViewSet,
    basename="optimized-borrow-records",
)

urlpatterns = router.urls
