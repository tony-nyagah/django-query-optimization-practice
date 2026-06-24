"""Optimized seed command using bulk_create instead of .save() in a loop.

Demonstrates the performance difference:
- Naive: .save() per object → 1 INSERT per row
- Optimized: bulk_create() → 1 INSERT for all rows

For 5000 books, naive takes ~5000 round-trips to the database.
bulk_create sends all 5000 in a single INSERT.
"""

import random
import time

from django.core.management.base import BaseCommand
from django.db import transaction

from books.models import Book, Publisher


class Command(BaseCommand):
    help = "Seed books with bulk_create — compare against the naive seed_books command."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=5000,
            help="Number of books to seed (default: 5000)",
        )

    def handle(self, *args, **options):
        count = options["count"]

        # Ensure we have a publisher
        publisher, _ = Publisher.objects.get_or_create(
            name="Bulk Seed Press",
            defaults={"country": "US"},
        )

        # Naive: .save() in a loop
        self.stdout.write(f"Naive: Creating {count} books with .save() in a loop...")
        Book.objects.filter(publisher=publisher).delete()  # clean slate

        start = time.perf_counter()
        for i in range(count):
            Book.objects.create(
                title=f"Naive Book {i}",
                isbn=f"999000000{i:04d}"[:13],
                publisher=publisher,
                page_count=random.randint(50, 800),
                language="English",
            )
        naive_time = time.perf_counter() - start
        books_deleted, _ = Book.objects.filter(publisher=publisher).delete()
        self.stdout.write(f"  Created and deleted {books_deleted} books in {naive_time:.2f}s")

        # Optimized: bulk_create
        self.stdout.write(
            f"Optimized: Creating {count} books with bulk_create()..."
        )
        start = time.perf_counter()
        books = [
            Book(
                title=f"Bulk Book {i}",
                isbn=f"888000000{i:04d}"[:13],
                publisher=publisher,
                page_count=random.randint(50, 800),
                language="English",
            )
            for i in range(count)
        ]
        with transaction.atomic():
            Book.objects.bulk_create(books, batch_size=1000)
        bulk_time = time.perf_counter() - start

        self.stdout.write(
            self.style.SUCCESS(
                f"\nResults for {count} books:\n"
                f"  Naive (.save loop): {naive_time:.2f}s\n"
                f"  Optimized (bulk_create): {bulk_time:.2f}s\n"
                f"  Speedup: {naive_time / bulk_time:.1f}x"
            )
        )

        # Clean up
        Book.objects.filter(publisher=publisher).delete()
