from django.core.management.base import BaseCommand
from mimesis import Person
from mimesis.locales import Locale

from users.models import User

BATCH_SIZE = 100


class Command(BaseCommand):
    help = "Seeds the database with 1000 dummy users"

    def handle(self, *args, **options):
        person = Person(Locale.EN)

        existing_emails = set(User.objects.values_list("email", flat=True))
        users = []

        while len(users) < 1000:
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

        self.stdout.write(self.style.SUCCESS("Successfully seeded 1000 users."))
