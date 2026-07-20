"""Master seed command — idempotent, runs all seed steps in order.

Only executes when the database is empty (no Books exist), making it safe
to run on every deploy without duplicating data.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand

from books.models import Book


class Command(BaseCommand):
    help = "Seed the entire database (users, books, library data) if empty."

    def handle(self, *args, **options):
        if Book.objects.exists():
            self.stdout.write(
                self.style.SUCCESS("Database already seeded — nothing to do.")
            )
            return

        self.stdout.write("Seeding database for the first time…")
        self.stdout.write("")

        call_command("seed_users", count=1000)
        call_command("seed_books", books=5000, authors=300, publishers=100)
        call_command("seed_library", reviews_per_user=10, borrows_per_user=10)

        self.stdout.write(self.style.SUCCESS("\nDatabase seeded successfully."))
