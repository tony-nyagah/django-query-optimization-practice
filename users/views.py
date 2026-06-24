from django.db.models import Count
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import User
from .serializers import OptimizedUserSerializer, UnoptimizedUserSerializer


class UnoptimizedUserViewSet(viewsets.ReadOnlyModelViewSet):
    """Unoptimized endpoint — exposes the N+1 query problem on User.

    The serializer calls `user.reviews.count()`, `user.borrow_records.count()`,
    and `user.reading_lists.count()` for each user. Django fires a separate
    COUNT query per user per field.

    For a page of N users:
        1 query  — fetch users
        N queries — COUNT reviews per user      (N+1)
        N queries — COUNT borrow_records per user (N+1)
        N queries — COUNT reading_lists per user (N+1)

    Total: 3N + 1 queries.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UnoptimizedUserSerializer
    queryset = User.objects.all().order_by("email")


class OptimizedUserViewSet(viewsets.ReadOnlyModelViewSet):
    """Optimized endpoint for User.

    annotate() computes review_count, borrow_record_count, and
    reading_list_count directly in the main SQL query using LEFT OUTER JOIN
    and COUNT. All three values are available at zero extra query cost.

    Total: 1 query regardless of N.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = OptimizedUserSerializer

    def get_queryset(self):
        return User.objects.annotate(
            review_count=Count("reviews"),
            borrow_record_count=Count("borrow_records"),
            reading_list_count=Count("reading_lists"),
        ).order_by("email")
