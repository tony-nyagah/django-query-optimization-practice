"""Tests for user query optimization: annotate() vs SerializerMethodField counts."""

from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse

from books.models import Author, Book, BookAuthor, Genre, Publisher
from library.models import BorrowRecord, ReadingList, ReadingListEntry, Review
from .models import User


def count_queries(func):
    with override_settings(DEBUG=True):
        initial = len(connection.queries)
        func()
        return len(connection.queries) - initial


class UserQueryOptimizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unoptimized_url = reverse("unoptimized-users-list")
        cls.optimized_url = reverse("optimized-users-list")

        # Create users with related data to trigger COUNT queries
        cls.test_user = User.objects.create_user(
            email="auth@example.com",
            password="testpass123",
            first_name="Auth",
            last_name="User",
        )

        publisher = Publisher.objects.create(name="Test Press")
        author = Author.objects.create(first_name="A", last_name="B")
        genre = Genre.objects.create(name="Fiction", slug="fiction")
        book = Book.objects.create(
            title="Test Book", isbn="1234567890123", publisher=publisher
        )
        BookAuthor.objects.create(book=book, author=author)
        book.genres.add(genre)

        from django.utils import timezone
        from datetime import timedelta

        for i in range(5):
            user = User.objects.create_user(
                email=f"user{i}@example.com",
                password="testpass123",
                first_name=f"First{i}",
                last_name=f"Last{i}",
            )
            Review.objects.create(book=book, user=user, rating=4)
            BorrowRecord.objects.create(
                book=book, user=user, due_date=timezone.now() + timedelta(days=14)
            )
            ReadingList.objects.create(user=user, name=f"List {i}")

    def setUp(self):
        self.client.force_login(self.test_user)

    def test_unoptimized_fires_multiple_queries(self):
        """Unoptimized users fires N queries per user for each count."""
        total = count_queries(lambda: self.client.get(self.unoptimized_url))
        # Should be many — at least 3 count queries per user
        self.assertGreater(total, 10)

    def test_optimized_fires_fewer_queries(self):
        optimized = count_queries(lambda: self.client.get(self.optimized_url))
        unoptimized = count_queries(lambda: self.client.get(self.unoptimized_url))
        self.assertLess(optimized, unoptimized)

    def test_optimized_hits_target(self):
        total = count_queries(lambda: self.client.get(self.optimized_url))
        # 1 query with annotated counts
        self.assertLessEqual(total, 3)
