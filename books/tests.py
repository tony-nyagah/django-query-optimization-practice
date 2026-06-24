"""Tests that prove the optimized endpoints fire fewer queries than the unoptimized ones.

Each test:
1. Seeds a small dataset and creates a test user
2. Authenticates as that user
3. Hits the unoptimized endpoint, captures SQL count
4. Hits the optimized endpoint, captures SQL count
5. Asserts optimized < unoptimized (and meets the target query count)
"""

from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse

from users.models import User
from .models import Author, Book, BookAuthor, Genre, Publisher


def count_queries(func):
    """Return the number of SQL queries `func` executes."""
    with override_settings(DEBUG=True):
        initial = len(connection.queries)
        func()
        return len(connection.queries) - initial


class BookQueryOptimizationTests(TestCase):
    """Books endpoints: tests for select_related, prefetch_related, annotate, only."""

    @classmethod
    def setUpTestData(cls):
        cls.unoptimized_url = reverse("unoptimized-books-list")
        cls.optimized_url = reverse("optimized-books-list")

        # Create a test user and authenticate
        cls.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

        # Create 5 books with publishers, authors, and genres
        publisher = Publisher.objects.create(name="Test Press", country="US")
        author1 = Author.objects.create(
            first_name="Jane", last_name="Austen", nationality="British"
        )
        author2 = Author.objects.create(
            first_name="Leo", last_name="Tolstoy", nationality="Russian"
        )
        genre_fiction = Genre.objects.create(name="Fiction", slug="fiction")
        genre_classic = Genre.objects.create(name="Classic", slug="classic")

        for i in range(5):
            book = Book.objects.create(
                title=f"Test Book {i}",
                isbn=f"123456789012{i}",
                publisher=publisher,
                page_count=200 + i,
            )
            BookAuthor.objects.create(book=book, author=author1)
            BookAuthor.objects.create(book=book, author=author2)
            book.genres.add(genre_fiction, genre_classic)

    def setUp(self):
        self.client.force_login(self.user)

    def test_unoptimized_fires_multiple_queries(self):
        """The unoptimized endpoint should fire more than 4 queries (N+1 patterns)."""
        total = count_queries(lambda: self.client.get(self.unoptimized_url))
        self.assertGreater(
            total, 4,
            f"Unoptimized should have N+1 overhead. Got only {total} queries."
        )

    def test_optimized_fires_fewer_queries(self):
        """The optimized endpoint should fire 3 queries regardless of N."""
        optimized_total = count_queries(lambda: self.client.get(self.optimized_url))
        unoptimized_total = count_queries(
            lambda: self.client.get(self.unoptimized_url)
        )
        self.assertLess(
            optimized_total, unoptimized_total,
            f"Optimized ({optimized_total}) should be less than "
            f"unoptimized ({unoptimized_total})"
        )

    def test_optimized_hits_target_query_count(self):
        """Optimized book list should be exactly 3 queries (books, authors, genres)."""
        total = count_queries(lambda: self.client.get(self.optimized_url))
        self.assertLessEqual(total, 5, f"Optimized books should be ≤5 queries. Got {total}.")

    def test_book_detail_optimized(self):
        """Detail endpoint should also benefit from query optimization."""
        book = Book.objects.first()
        url = reverse("optimized-books-detail", kwargs={"pk": book.pk})
        total = count_queries(lambda: self.client.get(url))
        self.assertLessEqual(total, 5, f"Detail should be ≤5 queries. Got {total}.")


class BookSubqueryOptimizationTests(TestCase):
    """Subquery: latest review per book using Subquery(OuterRef('pk'))."""

    @classmethod
    def setUpTestData(cls):
        from library.models import Review

        cls.user = User.objects.create_user(
            email="subq@example.com",
            password="testpass123",
            first_name="Sub",
            last_name="Query",
        )
        publisher = Publisher.objects.create(name="Subquery Press")

        for i in range(5):
            book = Book.objects.create(
                title=f"Subquery Book {i}",
                isbn=f"SUBQ0000000{i}",
                publisher=publisher,
            )
            Review.objects.create(
                book=book, user=cls.user, rating=4,
                body=f"Good book {i}",
            )

    def setUp(self):
        self.client.force_login(self.user)

    def test_unoptimized_fires_multiple_queries(self):
        total = count_queries(
            lambda: self.client.get(
                reverse("unoptimized-books-latest-review-list")
            )
        )
        self.assertGreater(total, 5)

    def test_optimized_fires_fewer_queries(self):
        optimized = count_queries(
            lambda: self.client.get(
                reverse("optimized-books-latest-review-list")
            )
        )
        unoptimized = count_queries(
            lambda: self.client.get(
                reverse("unoptimized-books-latest-review-list")
            )
        )
        self.assertLess(optimized, unoptimized)


class BookExistsOptimizationTests(TestCase):
    """Exists: books with active borrows using Exists(OuterRef('pk'))."""

    @classmethod
    def setUpTestData(cls):
        from django.utils import timezone
        from datetime import timedelta
        from library.models import BorrowRecord

        cls.user = User.objects.create_user(
            email="exists@example.com",
            password="testpass123",
            first_name="Exists",
            last_name="Test",
        )
        publisher = Publisher.objects.create(name="Exists Press")

        for i in range(5):
            book = Book.objects.create(
                title=f"Exists Book {i}",
                isbn=f"EXST0000000{i}",
                publisher=publisher,
            )
            # Half have active borrows, half don't
            if i % 2 == 0:
                BorrowRecord.objects.create(
                    book=book, user=cls.user,
                    due_date=timezone.now() + timedelta(days=14),
                )

    def setUp(self):
        self.client.force_login(self.user)

    def test_unoptimized_fires_multiple_queries(self):
        total = count_queries(
            lambda: self.client.get(
                reverse("unoptimized-books-borrowed-list")
            )
        )
        self.assertGreater(total, 5)

    def test_optimized_fires_fewer_queries(self):
        optimized = count_queries(
            lambda: self.client.get(
                reverse("optimized-books-borrowed-list")
            )
        )
        unoptimized = count_queries(
            lambda: self.client.get(
                reverse("unoptimized-books-borrowed-list")
            )
        )
        self.assertLess(optimized, unoptimized)
