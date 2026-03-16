from rest_framework import serializers

from .models import BorrowRecord, ReadingList, ReadingListEntry, Review


class ReviewSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "user_email",
            "book_title",
            "rating",
            "body",
            "is_spoiler",
            "created_at",
        ]


class ReadingListEntrySerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    book_isbn = serializers.CharField(source="book.isbn", read_only=True)
    status = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ReadingListEntry
        fields = ["id", "book_title", "book_isbn", "status", "order", "date_added"]


class ReadingListSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    entries = ReadingListEntrySerializer(many=True, read_only=True)
    entry_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ReadingList
        fields = [
            "id",
            "user_email",
            "name",
            "is_public",
            "entry_count",
            "entries",
            "created_at",
        ]


class BorrowRecordSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = BorrowRecord
        fields = [
            "id",
            "user_email",
            "book_title",
            "borrowed_at",
            "due_date",
            "returned_at",
            "is_overdue",
        ]
