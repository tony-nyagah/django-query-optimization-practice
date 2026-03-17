from django.core.management.base import BaseCommand
from mimesis import Person
from mimesis.locales import Locale

from users.models import User

BATCH_SIZE = 100


class Command(BaseCommand):
    help = "Seeds the database with dummy users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=1000,
            help="Number of users to create (default: 1000)",
        )

    def handle(self, *args, **options):
        count = options["count"]
        person = Person(Locale.EN)

        existing_emails = set(User.objects.values_list("email", flat=True))
        users = []

        while len(users) < count:
            email = person.email()
            if email in existing_emails:
                continue
            existing_emails.add(email)
            users.append(
                User(
                    email=email,
                    first_name=person.first_name(),
                    last_name=person.last_name(),
                    phone=person.telephone()[:20],
                    password="password123",  # unusable password
                )
            )

        User.objects.bulk_create(users, batch_size=BATCH_SIZE)

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {count} users."))
