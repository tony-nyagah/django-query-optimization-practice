from django.conf import settings
from django.db import models


class Review(models.Model):
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField()  # 1–5
    body = models.TextField(blank=True)
    is_spoiler = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("book", "user")

    def __str__(self):
        return f"{self.user} → {self.book} ({self.rating}★)"


class ReadingList(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reading_lists",
    )
    name = models.CharField(max_length=255)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("user", "name")

    def __str__(self):
        return f"{self.user} — {self.name}"


class ReadingListEntry(models.Model):
    class Status(models.TextChoices):
        WANT_TO_READ = "want_to_read", "Want to Read"
        READING = "reading", "Reading"
        FINISHED = "finished", "Finished"
        ABANDONED = "abandoned", "Abandoned"

    reading_list = models.ForeignKey(
        ReadingList,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.CASCADE,
        related_name="reading_list_entries",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.WANT_TO_READ
    )
    date_added = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "date_added"]
        unique_together = ("reading_list", "book")

    def __str__(self):
        return (
            f"{self.book} in '{self.reading_list.name}' ({self.get_status_display()})"
        )


class BorrowRecord(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="borrow_records",
    )
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.CASCADE,
        related_name="borrow_records",
    )
    borrowed_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-borrowed_at"]

    def __str__(self):
        return f"{self.user} borrowed '{self.book}' on {self.borrowed_at:%Y-%m-%d}"

    @property
    def is_overdue(self) -> bool:
        from django.utils import timezone

        return self.returned_at is None and self.due_date < timezone.now()
