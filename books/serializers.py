from rest_framework import serializers

from .models import Author, Book, BookAuthor, Genre, Publisher


class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ["id", "name", "country", "website"]


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "first_name", "last_name", "nationality"]


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name", "slug"]


class BookAuthorSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()
    role = serializers.CharField(source="get_role_display")

    class Meta:
        model = BookAuthor
        fields = ["author", "role"]


class UnoptimizedBookSerializer(serializers.ModelSerializer):
    """
    Naive serializer — accesses publisher, authors, and genres as separate
    attributes on each book instance. When used in a list view with no
    prefetching, this triggers:

        1 query  — fetch books
        N queries — fetch each book's publisher  (N+1)
        N queries — fetch each book's authors    (N+1)
        N queries — fetch each book's genres     (N+1)
        N queries — count each book's authors in Python (N+1)

    Total: 4N + 1 queries.
    """

    publisher = PublisherSerializer()
    authors = BookAuthorSerializer(source="book_authors", many=True)
    genres = GenreSerializer(many=True)
    author_count = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "isbn",
            "publisher",
            "authors",
            "genres",
            "author_count",
            "published_date",
            "page_count",
            "language",
            "average_rating",
        ]

    def get_author_count(self, obj):
        return obj.authors.count()


class OptimizedBookSerializer(serializers.ModelSerializer):
    """
    Optimized serializer — relies on the queryset already having fetched
    all related data. Works together with OptimizedBookViewSet which uses:

        select_related('publisher')       — JOIN for the FK, zero extra queries
        prefetch_related('book_authors__author', 'genres') — 2 extra queries total
        annotate(author_count=Count('authors')) — COUNT in SQL, zero extra queries
        only(...)                         — limits columns fetched from the DB

    Total: 3 queries regardless of N.
    """

    publisher = PublisherSerializer()
    authors = BookAuthorSerializer(source="book_authors", many=True)
    genres = GenreSerializer(many=True)
    author_count = serializers.IntegerField()

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "isbn",
            "publisher",
            "authors",
            "genres",
            "author_count",
            "published_date",
            "page_count",
            "language",
            "average_rating",
        ]


# ---------------------------------------------------------------------------
# Subquery technique: annotate each book with its latest review
# ---------------------------------------------------------------------------



class UnoptimizedBookWithLatestReviewSerializer(serializers.ModelSerializer):
    """
    Naive approach: uses SerializerMethodField to fetch the latest review
    per book in Python. Fires a separate query per book.

    For N books: 1 query + N queries = N+1.
    """

    latest_review_body = serializers.SerializerMethodField()
    latest_review_rating = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ["id", "title", "latest_review_body", "latest_review_rating"]

    def get_latest_review_body(self, obj):
        review = obj.reviews.order_by("-created_at").first()
        return review.body if review else None

    def get_latest_review_rating(self, obj):
        review = obj.reviews.order_by("-created_at").first()
        return review.rating if review else None


class OptimizedBookWithLatestReviewSerializer(serializers.ModelSerializer):
    """
    Optimized approach: the queryset annotates each book with
    latest_review_body and latest_review_rating via Subquery.
    The serializer reads these annotated fields — zero extra queries.
    """

    latest_review_body = serializers.CharField(read_only=True)
    latest_review_rating = serializers.IntegerField(read_only=True)

    class Meta:
        model = Book
        fields = ["id", "title", "latest_review_body", "latest_review_rating"]


# ---------------------------------------------------------------------------
# Exists technique: filter books that have active borrows
# ---------------------------------------------------------------------------


class UnoptimizedBookBorrowedSerializer(serializers.ModelSerializer):
    """
    Naive approach: SerializerMethodField checks borrow_records per book.
    Fires a query per book to check if it has active borrows.

    For N books: 1 query + N queries = N+1.
    """

    has_active_borrows = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ["id", "title", "isbn", "has_active_borrows"]

    def get_has_active_borrows(self, obj):
        return obj.borrow_records.filter(returned_at__isnull=True).exists()


class OptimizedBookBorrowedSerializer(serializers.ModelSerializer):
    """
    Optimized approach: the queryset annotates each book with an Exists
    subquery. The serializer reads the boolean — zero extra queries.
    """

    has_active_borrows = serializers.BooleanField()

    class Meta:
        model = Book
        fields = ["id", "title", "isbn", "has_active_borrows"]
