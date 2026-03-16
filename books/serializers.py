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
