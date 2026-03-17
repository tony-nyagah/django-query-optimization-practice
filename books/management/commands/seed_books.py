import random
from datetime import date

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from mimesis import Person, Text
from mimesis.locales import Locale
from mimesis.providers.address import Address

from books.models import Author, Book, BookAuthor, BookGenre, Genre, Publisher

GENRES = [
    "Fiction",
    "Non-Fiction",
    "Mystery",
    "Science Fiction",
    "Fantasy",
    "Romance",
    "Thriller",
    "Biography",
    "History",
    "Self-Help",
    "Horror",
    "Poetry",
    "Children's",
    "Young Adult",
    "Graphic Novel",
    "Science",
    "Travel",
    "Cooking",
    "Philosophy",
    "Psychology",
]

LANGUAGES = ["English", "French", "Spanish", "German", "Portuguese", "Italian"]


class Command(BaseCommand):
    help = "Seeds the database with publishers, authors, genres, and books"

    def add_arguments(self, parser):
        parser.add_argument(
            "--books",
            type=int,
            default=5000,
            help="Number of books to create (default: 5000)",
        )
        parser.add_argument(
            "--authors",
            type=int,
            default=300,
            help="Number of authors to create (default: 300)",
        )
        parser.add_argument(
            "--publishers",
            type=int,
            default=100,
            help="Number of publishers to create (default: 100)",
        )

    def handle(self, *args, **options):
        self.num_books = options["books"]
        self.num_authors = options["authors"]
        self.num_publishers = options["publishers"]
        self.seed_genres()
        self.seed_publishers()
        self.seed_authors()
        self.seed_books()

    def seed_genres(self):
        created = 0
        for name in GENRES:
            slug = slugify(name)
            _, was_created = Genre.objects.get_or_create(
                slug=slug, defaults={"name": name}
            )
            if was_created:
                created += 1
        self.stdout.write(
            f"  Genres: {created} created, {len(GENRES) - created} already existed."
        )

    def seed_publishers(self):
        person = Person(Locale.EN)
        address = Address(Locale.EN)
        publishers = []
        existing = set(Publisher.objects.values_list("name", flat=True))

        while len(publishers) < self.num_publishers:
            name = f"{person.last_name()} {random.choice(['Publishing', 'Press', 'Books', 'Media', 'House'])}"
            if name in existing:
                continue
            existing.add(name)
            publishers.append(
                Publisher(
                    name=name,
                    country=address.country(),
                    website=f"https://www.{slugify(name)}.com",
                )
            )

        Publisher.objects.bulk_create(publishers)
        self.stdout.write(f"  Publishers: {len(publishers)} created.")

    def seed_authors(self):
        person = Person(Locale.EN)
        authors = []
        existing = set(Author.objects.values_list("first_name", "last_name"))

        while len(authors) < self.num_authors:
            first_name = person.first_name()
            last_name = person.last_name()
            if (first_name, last_name) in existing:
                continue
            existing.add((first_name, last_name))
            birth_year = random.randint(1920, 1995)
            authors.append(
                Author(
                    first_name=first_name,
                    last_name=last_name,
                    birth_date=date(
                        birth_year, random.randint(1, 12), random.randint(1, 28)
                    ),
                    nationality=Person(Locale.EN).nationality(),
                )
            )

        Author.objects.bulk_create(authors)
        self.stdout.write(f"  Authors: {len(authors)} created.")

    def seed_books(self):
        text = Text(Locale.EN)

        publishers = list(Publisher.objects.all())
        authors = list(Author.objects.all())
        genres = list(Genre.objects.all())

        existing_isbns = set(Book.objects.values_list("isbn", flat=True))
        books = []

        while len(books) < self.num_books:
            isbn = str(random.randint(1000000000000, 9999999999999))
            if isbn in existing_isbns:
                continue
            existing_isbns.add(isbn)
            pub_year = random.randint(1950, 2024)
            books.append(
                Book(
                    title=text.title(),
                    isbn=isbn,
                    publisher=random.choice(publishers),
                    published_date=date(
                        pub_year, random.randint(1, 12), random.randint(1, 28)
                    ),
                    page_count=random.randint(80, 1200),
                    language=random.choice(LANGUAGES),
                    average_rating=round(random.uniform(1.0, 5.0), 2),
                )
            )

        Book.objects.bulk_create(books, batch_size=500)
        self.stdout.write(f"  Books: {len(books)} created.")

        # Assign authors to books
        all_books = list(Book.objects.all())
        roles = [choice[0] for choice in BookAuthor.Role.choices]
        book_authors = []
        for book in all_books:
            # 1 primary author always, chance of additional co-authors
            num_authors = random.choices([1, 2, 3], weights=[70, 20, 10])[0]
            selected_authors = random.sample(authors, k=num_authors)
            for i, author in enumerate(selected_authors):
                role = BookAuthor.Role.PRIMARY if i == 0 else random.choice(roles[1:])
                book_authors.append(BookAuthor(book=book, author=author, role=role))

        BookAuthor.objects.bulk_create(
            book_authors, batch_size=500, ignore_conflicts=True
        )
        self.stdout.write(f"  BookAuthors: {len(book_authors)} assignments created.")

        # Assign genres to books — each book gets 1 to 3 genres
        book_genres = []
        for book in all_books:
            num_genres = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
            selected_genres = random.sample(genres, k=num_genres)
            for genre in selected_genres:
                book_genres.append(BookGenre(book=book, genre=genre))

        BookGenre.objects.bulk_create(
            book_genres, batch_size=500, ignore_conflicts=True
        )
        self.stdout.write(f"  BookGenres: {len(book_genres)} assignments created.")

        self.stdout.write(self.style.SUCCESS("Done! Database seeded successfully."))
