from rest_framework import serializers

from .models import User


class UnoptimizedUserSerializer(serializers.ModelSerializer):
    """Naive serializer — uses SerializerMethodField for each count,
    which fires a separate COUNT query per user per field.
    For N users: 1 query + 3N count queries = 3N+1 total."""

    review_count = serializers.SerializerMethodField()
    borrow_record_count = serializers.SerializerMethodField()
    reading_list_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "review_count",
            "borrow_record_count",
            "reading_list_count",
        ]

    def get_review_count(self, obj):
        return obj.reviews.count()

    def get_borrow_record_count(self, obj):
        return obj.borrow_records.count()

    def get_reading_list_count(self, obj):
        return obj.reading_lists.count()


class OptimizedUserSerializer(serializers.ModelSerializer):
    """Optimized serializer — uses IntegerField backed by annotate()
    in the queryset. All three counts are computed in the main SQL query,
    so accessing them costs zero extra queries."""

    review_count = serializers.IntegerField()
    borrow_record_count = serializers.IntegerField()
    reading_list_count = serializers.IntegerField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "review_count",
            "borrow_record_count",
            "reading_list_count",
        ]
