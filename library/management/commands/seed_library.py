import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from books.models import Book
from library.models import BorrowRecord, ReadingList, ReadingListEntry, Review

User = get_user_model()

READING_LIST_NAMES = [
    "To Read",
    "Favourites",
    "Currently Reading",
    "Classics",
    "Recommended",
    "Book Club",
    "Holiday Reads",
    "Must Reads",
]


class Command(BaseCommand):
    help = "Seeds the database with reviews, reading lists, and borrow records"

    def handle(self, *args, **options):
        users = list(User.objects.all())
        books = list(Book.objects.all())

        if not users:
            self.stdout.write(self.style.ERROR("No users found. Run seed_users first."))
            return

        if not books:
            self.stdout.write(self.style.ERROR("No books found. Run seed_books first."))
            return

        self.seed_reviews(users, books)
        self.seed_reading_lists(users, books)
        self.seed_borrow_records(users, books)

    def seed_reviews(self, users, books):
        existing = set(Review.objects.values_list("user_id", "book_id"))
        reviews = []

        for user in users:
            num_reviews = random.randint(1, 10)
            sampled_books = random.sample(books, k=min(num_reviews, len(books)))
            for book in sampled_books:
                if (user.id, book.id) in existing:
                    continue
                existing.add((user.id, book.id))
                reviews.append(
                    Review(
                        user=user,
                        book=book,
                        rating=random.randint(1, 5),
                        body=""
                        if random.random() < 0.3
                        else f"Review of {book.title}.",
                        is_spoiler=random.random() < 0.1,
                    )
                )

        Review.objects.bulk_create(reviews, batch_size=500)
        self.stdout.write(f"  Reviews: {len(reviews)} created.")

    def seed_reading_lists(self, users, books):
        reading_lists_created = 0
        entries_created = 0
        statuses = [choice[0] for choice in ReadingListEntry.Status.choices]

        for user in users:
            num_lists = random.randint(1, 3)
            names = random.sample(READING_LIST_NAMES, k=num_lists)

            for name in names:
                reading_list, created = ReadingList.objects.get_or_create(
                    user=user,
                    name=name,
                    defaults={"is_public": random.random() < 0.4},
                )
                if created:
                    reading_lists_created += 1

                existing_book_ids = set(
                    reading_list.entries.values_list("book_id", flat=True)
                )
                num_entries = random.randint(5, 20)
                sampled_books = random.sample(books, k=min(num_entries, len(books)))
                entries = []
                for order, book in enumerate(sampled_books):
                    if book.id in existing_book_ids:
                        continue
                    existing_book_ids.add(book.id)
                    entries.append(
                        ReadingListEntry(
                            reading_list=reading_list,
                            book=book,
                            status=random.choice(statuses),
                            order=order,
                        )
                    )
                ReadingListEntry.objects.bulk_create(
                    entries, batch_size=500, ignore_conflicts=True
                )
                entries_created += len(entries)

        self.stdout.write(f"  ReadingLists: {reading_lists_created} created.")
        self.stdout.write(f"  ReadingListEntries: {entries_created} created.")

    def seed_borrow_records(self, users, books):
        now = timezone.now()
        records = []

        for user in users:
            num_borrows = random.randint(1, 10)
            sampled_books = random.sample(books, k=min(num_borrows, len(books)))

            for book in sampled_books:
                borrowed_at = now - timedelta(days=random.randint(1, 180))
                due_date = borrowed_at + timedelta(days=14)

                # 60% returned, 25% still out (some overdue), 15% overdue and not returned
                roll = random.random()
                if roll < 0.6:
                    returned_at = due_date - timedelta(days=random.randint(0, 7))
                elif roll < 0.85:
                    returned_at = None  # still out, due in future
                    due_date = now + timedelta(days=random.randint(1, 14))
                else:
                    returned_at = None  # overdue

                records.append(
                    BorrowRecord(
                        user=user,
                        book=book,
                        due_date=due_date,
                        returned_at=returned_at,
                    )
                )

        BorrowRecord.objects.bulk_create(records, batch_size=500)
        self.stdout.write(f"  BorrowRecords: {len(records)} created.")
        self.stdout.write(self.style.SUCCESS("Done! Library data seeded successfully."))
