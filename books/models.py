from django.db import models


class Publisher(models.Model):
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Author(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birth_date = models.DateField(null=True, blank=True)
    bio = models.TextField(blank=True)
    nationality = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Genre(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, unique=True)
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="books",
    )
    authors = models.ManyToManyField(
        Author,
        through="BookAuthor",
        related_name="books",
    )
    genres = models.ManyToManyField(
        Genre,
        through="BookGenre",
        related_name="books",
    )
    published_date = models.DateField(null=True, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    cover_image_url = models.URLField(blank=True)
    language = models.CharField(max_length=50, default="English")
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True
    )

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class BookAuthor(models.Model):
    class Role(models.TextChoices):
        PRIMARY = "primary", "Primary Author"
        CO_AUTHOR = "co_author", "Co-Author"
        ILLUSTRATOR = "illustrator", "Illustrator"
        EDITOR = "editor", "Editor"

    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="book_authors"
    )
    author = models.ForeignKey(
        Author, on_delete=models.CASCADE, related_name="book_authors"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PRIMARY)

    class Meta:
        unique_together = ("book", "author")

    def __str__(self):
        return f"{self.author} — {self.book} ({self.get_role_display()})"


class BookGenre(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="book_genres")
    genre = models.ForeignKey(
        Genre, on_delete=models.CASCADE, related_name="book_genres"
    )

    class Meta:
        unique_together = ("book", "genre")

    def __str__(self):
        return f"{self.book} — {self.genre}"
