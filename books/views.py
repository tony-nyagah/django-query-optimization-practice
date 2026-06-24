from django.db.models import Count, Exists, OuterRef, Prefetch, Subquery
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from library.models import BorrowRecord, Review
from .models import Book, BookAuthor
from .serializers import (
    OptimizedBookBorrowedSerializer,
    OptimizedBookSerializer,
    OptimizedBookWithLatestReviewSerializer,
    UnoptimizedBookBorrowedSerializer,
    UnoptimizedBookSerializer,
    UnoptimizedBookWithLatestReviewSerializer,
)


class UnoptimizedBookViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Unoptimized endpoint — exposes the N+1 query problem.

    The queryset fetches books with no prefetching or annotation.
    Each time the serializer accesses `publisher`, `book_authors`, `genres`,
    or calls `authors.count()` on a book, Django fires a separate query.

    For a page of N books that means:
        1 query  — fetch books
        N queries — fetch each book's publisher      (N+1)
        N queries — fetch each book's book_authors   (N+1)
        N queries — fetch each book's genres         (N+1)
        N queries — count each book's authors        (N+1)

    Total: 4N + 1 queries. With a page size of 10 that's 41 queries.
    Open the Django Debug Toolbar to see this in action.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UnoptimizedBookSerializer

    def get_queryset(self):
        return Book.objects.all()


class OptimizedBookViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Optimized endpoint — demonstrates four ORM optimization techniques.

    1. select_related('publisher')
       Performs a SQL JOIN between books and publishers so both are fetched
       in the same query. Accessing `book.publisher` costs zero extra queries.

    2. prefetch_related(Prefetch('book_authors__author'))
       Fetches all BookAuthor rows (and their related Author rows) for all
       books in one extra query, then maps them in Python. Accessing
       `book.book_authors.all()` costs zero extra queries.

    3. prefetch_related('genres')
       Fetches all Genre rows for all books in one extra query via the
       BookGenre through table. Accessing `book.genres.all()` costs zero
       extra queries.

    4. annotate(author_count=Count('authors'))
       Adds a COUNT() to the main SQL query so the total number of authors
       per book is computed in the database. No extra query needed.

    5. only(...)
       Limits the columns fetched from the books table to only what the
       serializer actually uses. Avoids pulling unused data over the wire.

    Total: 3 queries regardless of N.
    Compare this against the unoptimized endpoint.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = OptimizedBookSerializer

    def get_queryset(self):
        book_authors_prefetch = Prefetch(
            "book_authors",
            queryset=BookAuthor.objects.select_related("author"),
        )

        return (
            Book.objects.select_related("publisher")
            .prefetch_related(book_authors_prefetch, "genres")
            .annotate(author_count=Count("authors"))
            .only(
                "id",
                "title",
                "isbn",
                "publisher",
                "published_date",
                "page_count",
                "language",
                "average_rating",
            )
        )


# ---------------------------------------------------------------------------
# Subquery: latest review per book
# ---------------------------------------------------------------------------


class UnoptimizedBookLatestReviewViewSet(viewsets.ReadOnlyModelViewSet):
    """Unoptimized: fetches latest review per book via SerializerMethodField.

    The serializer calls `obj.reviews.order_by('-created_at').first()` for
    each book. That's a separate SQL query per book.

    Total: N + 1 queries.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UnoptimizedBookWithLatestReviewSerializer

    def get_queryset(self):
        return Book.objects.all()


class OptimizedBookLatestReviewViewSet(viewsets.ReadOnlyModelViewSet):
    """Optimized: annotates each book with its latest review via Subquery.

    Subquery with OuterRef runs a single correlated subquery that fetches
    the latest review data for all books in one SQL operation.

    Total: 1 query (the subquery is embedded in the main query).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = OptimizedBookWithLatestReviewSerializer

    def get_queryset(self):
        latest_review = (
            Review.objects.filter(book=OuterRef("pk"))
            .order_by("-created_at")
            .values("body")[:1]
        )
        latest_review_rating = (
            Review.objects.filter(book=OuterRef("pk"))
            .order_by("-created_at")
            .values("rating")[:1]
        )

        return Book.objects.annotate(
            latest_review_body=Subquery(latest_review),
            latest_review_rating=Subquery(latest_review_rating),
        ).only("id", "title")


# ---------------------------------------------------------------------------
# Exists: books with active borrows
# ---------------------------------------------------------------------------


class UnoptimizedBookBorrowedViewSet(viewsets.ReadOnlyModelViewSet):
    """Unoptimized: checks `has_active_borrows` per book in Python.

    The serializer calls `obj.borrow_records.filter(returned_at__isnull=True).exists()`
    for each book — N extra EXISTS queries.

    Total: N + 1 queries.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UnoptimizedBookBorrowedSerializer

    def get_queryset(self):
        return Book.objects.all()


class OptimizedBookBorrowedViewSet(viewsets.ReadOnlyModelViewSet):
    """Optimized: annotates with Exists subquery.

    Exists(OuterRef('pk')) embeds the EXISTS check directly in the main
    SQL query. The database resolves it in one pass.

    Total: 1 query.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = OptimizedBookBorrowedSerializer

    def get_queryset(self):
        has_active = BorrowRecord.objects.filter(
            book=OuterRef("pk"),
            returned_at__isnull=True,
        )
        return Book.objects.annotate(
            has_active_borrows=Exists(has_active)
        ).only("id", "title", "isbn")
