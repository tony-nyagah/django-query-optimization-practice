"""Tests that prove the library endpoints' query optimizations actually work.

Each resource (reviews, reading lists, borrow records) has an unoptimized
and optimized endpoint. These tests verify the optimized version fires
fewer queries than the unoptimized one.
"""

from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from books.models import Author, Book, BookAuthor, Genre, Publisher
from users.models import User
from .models import BorrowRecord, ReadingList, ReadingListEntry, Review


def count_queries(func):
    """Return the number of SQL queries `func` executes."""
    with override_settings(DEBUG=True):
        initial = len(connection.queries)
        func()
        return len(connection.queries) - initial


class LibraryTestDataMixin:
    """Shared test data for all library test cases."""

    @classmethod
    def setUpTestData(cls):
        # Shared book data
        publisher = Publisher.objects.create(name="Test Press", country="US")
        author = Author.objects.create(
            first_name="Jane", last_name="Austen", nationality="British"
        )
        genre = Genre.objects.create(name="Fiction", slug="fiction")

        cls.books = []
        for i in range(5):
            book = Book.objects.create(
                title=f"Test Book {i}",
                isbn=f"123456789012{i}",
                publisher=publisher,
                page_count=200 + i,
            )
            BookAuthor.objects.create(book=book, author=author)
            book.genres.add(genre)
            cls.books.append(book)

        cls.users = []
        for i in range(3):
            user = User.objects.create_user(
                email=f"test{i}@example.com",
                password="testpass123",
                first_name=f"First{i}",
                last_name=f"Last{i}",
            )
            cls.users.append(user)

        # Auth user
        cls.test_user = cls.users[0]

        cls.reviews = []
        for i in range(10):
            review = Review.objects.create(
                book=cls.books[i % 5],
                user=cls.users[i % 3],
                rating=(i % 5) + 1,
                body=f"Review body {i}",
            )
            cls.reviews.append(review)

        cls.reading_lists = []
        for i in range(3):
            rl = ReadingList.objects.create(
                user=cls.users[i],
                name=f"List {i}",
                is_public=True,
            )
            for j in range(3):
                ReadingListEntry.objects.create(
                    reading_list=rl,
                    book=cls.books[j],
                    status=ReadingListEntry.Status.WANT_TO_READ,
                    order=j,
                )
            cls.reading_lists.append(rl)

        cls.borrow_records = []
        for i in range(10):
            record = BorrowRecord.objects.create(
                book=cls.books[i % 5],
                user=cls.users[i % 3],
                due_date=timezone.now() + timedelta(days=14),
            )
            cls.borrow_records.append(record)

    def setUp(self):
        self.client.force_login(self.test_user)


class ReviewQueryOptimizationTests(LibraryTestDataMixin, TestCase):
    """Review endpoints: select_related('user', 'book') should cut N+1."""

    def test_unoptimized_fires_multiple_queries(self):
        total = count_queries(
            lambda: self.client.get(reverse("unoptimized-reviews-list"))
        )
        self.assertGreater(total, 4)

    def test_optimized_fires_fewer_queries(self):
        optimized = count_queries(
            lambda: self.client.get(reverse("optimized-reviews-list"))
        )
        unoptimized = count_queries(
            lambda: self.client.get(reverse("unoptimized-reviews-list"))
        )
        self.assertLess(optimized, unoptimized)

    def test_optimized_hits_target(self):
        total = count_queries(
            lambda: self.client.get(reverse("optimized-reviews-list"))
        )
        self.assertLessEqual(total, 3)  # 1 review query + auth overhead


class ReadingListQueryOptimizationTests(LibraryTestDataMixin, TestCase):
    """Reading list endpoints: select_related, Prefetch, annotate."""

    def test_unoptimized_fires_multiple_queries(self):
        total = count_queries(
            lambda: self.client.get(reverse("unoptimized-reading-lists-list"))
        )
        self.assertGreater(total, 5)

    def test_optimized_fires_fewer_queries(self):
        optimized = count_queries(
            lambda: self.client.get(reverse("optimized-reading-lists-list"))
        )
        unoptimized = count_queries(
            lambda: self.client.get(reverse("unoptimized-reading-lists-list"))
        )
        self.assertLess(optimized, unoptimized)

    def test_optimized_hits_target(self):
        total = count_queries(
            lambda: self.client.get(reverse("optimized-reading-lists-list"))
        )
        self.assertLessEqual(total, 4)  # 2 queries + auth overhead


class BorrowRecordQueryOptimizationTests(LibraryTestDataMixin, TestCase):
    """Borrow record endpoints: select_related('user', 'book')."""

    def test_unoptimized_fires_multiple_queries(self):
        total = count_queries(
            lambda: self.client.get(reverse("unoptimized-borrow-records-list"))
        )
        self.assertGreater(total, 4)

    def test_optimized_fires_fewer_queries(self):
        optimized = count_queries(
            lambda: self.client.get(reverse("optimized-borrow-records-list"))
        )
        unoptimized = count_queries(
            lambda: self.client.get(reverse("unoptimized-borrow-records-list"))
        )
        self.assertLess(optimized, unoptimized)

    def test_optimized_hits_target(self):
        total = count_queries(
            lambda: self.client.get(reverse("optimized-borrow-records-list"))
        )
        self.assertLessEqual(total, 3)  # 1 query + auth overhead
