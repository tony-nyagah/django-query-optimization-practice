from django.db.models import Count, Prefetch
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Book, BookAuthor
from .serializers import OptimizedBookSerializer, UnoptimizedBookSerializer


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
