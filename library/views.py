from django.db.models import Count, Prefetch
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import BorrowRecord, ReadingList, ReadingListEntry, Review
from .serializers import (
    BorrowRecordSerializer,
    ReadingListSerializer,
    ReviewSerializer,
)

# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------


class UnoptimizedReviewViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Unoptimized endpoint — exposes the N+1 query problem on Review.

    The serializer accesses `review.user.email` and `review.book.title`
    for each review. With no prefetching Django fires a separate query
    per review to fetch the related user and book.

    For a page of N reviews:
        1 query  — fetch reviews
        N queries — fetch each review's user   (N+1)
        N queries — fetch each review's book   (N+1)

    Total: 2N + 1 queries.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        return Review.objects.all()


class OptimizedReviewViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Optimized endpoint for Review.

    select_related('user', 'book') performs a single SQL JOIN across
    reviews, users, and books so all three are fetched in one query.
    Accessing review.user or review.book costs zero extra queries.

    Total: 1 query regardless of N.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        return Review.objects.select_related("user", "book")


# ---------------------------------------------------------------------------
# Reading Lists
# ---------------------------------------------------------------------------


class UnoptimizedReadingListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Unoptimized endpoint — exposes multiple N+1 problems on ReadingList.

    The serializer accesses `reading_list.user.email`, iterates over
    `reading_list.entries.all()`, and for each entry accesses
    `entry.book.title` and `entry.book.isbn`. With no prefetching
    Django fires a separate query for each.

    For a page of N reading lists each with M entries:
        1 query  — fetch reading lists
        N queries — fetch each list's user          (N+1)
        N queries — fetch each list's entries       (N+1)
        N*M queries — fetch each entry's book       (N*M + 1)
        N queries — count each list's entries       (N+1)

    Total: 3N + (N*M) + 1 queries.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ReadingListSerializer

    def get_queryset(self):
        return ReadingList.objects.all()


class OptimizedReadingListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Optimized endpoint for ReadingList.

    1. select_related('user')
       JOINs users into the main query — zero extra queries for user access.

    2. prefetch_related(Prefetch('entries', queryset=...select_related('book')))
       Fetches all entries for all reading lists in one query, with their
       books JOINed in. Accessing entries and their books costs zero extra
       queries.

    3. annotate(entry_count=Count('entries'))
       Computes the entry count per list in SQL — zero extra queries.

    Total: 2 queries regardless of N.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ReadingListSerializer

    def get_queryset(self):
        entries_prefetch = Prefetch(
            "entries",
            queryset=ReadingListEntry.objects.select_related("book"),
        )

        return (
            ReadingList.objects.select_related("user")
            .prefetch_related(entries_prefetch)
            .annotate(entry_count=Count("entries"))
        )


# ---------------------------------------------------------------------------
# Borrow Records
# ---------------------------------------------------------------------------


class UnoptimizedBorrowRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Unoptimized endpoint — exposes the N+1 query problem on BorrowRecord.

    The serializer accesses `record.user.email` and `record.book.title`
    for each record. The `is_overdue` property on the model also accesses
    `record.due_date` and `record.returned_at` which are on the model
    itself (no extra query), but user and book each fire a query per row.

    For a page of N borrow records:
        1 query  — fetch borrow records
        N queries — fetch each record's user   (N+1)
        N queries — fetch each record's book   (N+1)

    Total: 2N + 1 queries.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = BorrowRecordSerializer

    def get_queryset(self):
        return BorrowRecord.objects.all()


class OptimizedBorrowRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Optimized endpoint for BorrowRecord.

    select_related('user', 'book') JOINs all three tables in one query.
    Accessing record.user or record.book costs zero extra queries.
    The is_overdue property reads fields already on the instance — no query.

    Total: 1 query regardless of N.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = BorrowRecordSerializer

    def get_queryset(self):
        return BorrowRecord.objects.select_related("user", "book")
