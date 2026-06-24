from rest_framework.routers import DefaultRouter

from .views import (
    OptimizedBookBorrowedViewSet,
    OptimizedBookLatestReviewViewSet,
    OptimizedBookViewSet,
    UnoptimizedBookBorrowedViewSet,
    UnoptimizedBookLatestReviewViewSet,
    UnoptimizedBookViewSet,
)

router = DefaultRouter()
router.register(
    r"books/unoptimized", UnoptimizedBookViewSet, basename="unoptimized-books"
)
router.register(r"books/optimized", OptimizedBookViewSet, basename="optimized-books")

# Subquery: latest review per book
router.register(
    r"books/latest-review/unoptimized",
    UnoptimizedBookLatestReviewViewSet,
    basename="unoptimized-books-latest-review",
)
router.register(
    r"books/latest-review/optimized",
    OptimizedBookLatestReviewViewSet,
    basename="optimized-books-latest-review",
)

# Exists: books with active borrows
router.register(
    r"books/borrowed/unoptimized",
    UnoptimizedBookBorrowedViewSet,
    basename="unoptimized-books-borrowed",
)
router.register(
    r"books/borrowed/optimized",
    OptimizedBookBorrowedViewSet,
    basename="optimized-books-borrowed",
)

urlpatterns = router.urls
