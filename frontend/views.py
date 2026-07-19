import time

from django.db import connections, reset_queries
from django.db.models import Count, Prefetch
from django.shortcuts import render

from books.models import Book, BookAuthor
from library.models import BorrowRecord, ReadingList, ReadingListEntry, Review
from users.models import User


def _measure(queryset, serializer_fn):
    """Run a query, measure query count and wall-clock time.

    Force-enables query logging even when DEBUG=False so the counter
    is accurate in production.
    """
    conn = connections["default"]
    old = conn.force_debug_cursor
    conn.force_debug_cursor = True
    reset_queries()
    start = time.perf_counter()
    try:
        data = serializer_fn(queryset)
    finally:
        elapsed = time.perf_counter() - start
        query_count = len(conn.queries)
        conn.force_debug_cursor = old
    return {"data": data, "queries": query_count, "time_ms": round(elapsed * 1000, 1)}


# ── Serializer helpers (simulate serializer output for the template) ─────────

def _book_row(book):
    return {
        "title": book.title,
        "authors": ", ".join(
            f"{ba.author.first_name} {ba.author.last_name} ({ba.get_role_display()})"
            for ba in book.book_authors.all()
        ),
        "publisher": book.publisher.name if book.publisher else "—",
        "genres": ", ".join(g.name for g in book.genres.all()),
        "pages": book.page_count or "—",
        "author_count": book.author_count if hasattr(book, "author_count") else book.authors.count(),
    }


def _review_row(review):
    return {
        "user": review.user.email,
        "book": review.book.title,
        "rating": "★" * review.rating,
        "spoiler": review.is_spoiler,
        "created": review.created_at.strftime("%b %d, %Y"),
    }


def _reading_list_row(rl):
    return {
        "name": rl.name,
        "user": rl.user.email,
        "public": rl.is_public,
        "entry_count": rl.entry_count if hasattr(rl, "entry_count") else rl.entries.count(),
        "entries": [
            {"book": e.book.title, "status": e.get_status_display()}
            for e in rl.entries.all()
        ],
    }


def _borrow_row(record):
    return {
        "user": record.user.email,
        "book": record.book.title,
        "borrowed": record.borrowed_at.strftime("%b %d, %Y"),
        "due": record.due_date.strftime("%b %d, %Y"),
        "overdue": record.is_overdue,
    }


# ── Views ───────────────────────────────────────────────────────────────────

def home(request):
    return render(request, "frontend/home.html")


def books(request):
    qs = Book.objects.all()

    unopt = _measure(qs, lambda q: [_book_row(b) for b in q[:20]])

    opt = _measure(
        qs.select_related("publisher")
        .prefetch_related(
            Prefetch("book_authors", queryset=BookAuthor.objects.select_related("author")),
            "genres",
        )
        .annotate(author_count=Count("authors"))[:20],
        lambda q: [_book_row(b) for b in q],
    )

    return render(request, "frontend/compare.html", {
        "title": "Books",
        "columns": ["Title", "Authors", "Publisher", "Genres", "Pages", "# Authors"],
        "unoptimized": unopt,
        "optimized": opt,
        "problem": "<code>publisher</code> is a ForeignKey — each book fires a separate query to fetch it. <code>book_authors</code>, <code>genres</code>, and <code>authors.count()</code> all fire per-row queries too. Result: <strong>4N+1 queries</strong>.",
        "unoptimized_code": "Book.objects.all()",
        "fix": "<code>select_related('publisher')</code> JOINs the publisher table into the main query. <code>prefetch_related('book_authors__author', 'genres')</code> fetches all related rows in 2 extra queries. <code>annotate(author_count=Count('authors'))</code> computes the count in SQL. Result: <strong>3 queries</strong> total.",
        "optimized_code": "Book.objects.select_related('publisher').prefetch_related(\n    Prefetch('book_authors', queryset=BookAuthor.objects.select_related('author')),\n    'genres',\n).annotate(author_count=Count('authors'))",
    })


def reviews(request):
    qs = Review.objects.all()

    unopt = _measure(qs, lambda q: [_review_row(r) for r in q[:20]])

    opt = _measure(
        qs.select_related("user", "book")[:20],
        lambda q: [_review_row(r) for r in q],
    )

    return render(request, "frontend/compare.html", {
        "title": "Reviews",
        "columns": ["User", "Book", "Rating", "Spoiler?", "Date"],
        "unoptimized": unopt,
        "optimized": opt,
        "problem": "The serializer accesses <code>review.user.email</code> and <code>review.book.title</code>. Both <code>user</code> and <code>book</code> are ForeignKeys — without optimization, each review fires 2 extra queries. Result: <strong>2N+1 queries</strong>.",
        "unoptimized_code": "Review.objects.all()",
        "fix": "<code>select_related('user', 'book')</code> performs SQL JOINs across reviews, users, and books in a single query. Accessing <code>review.user</code> or <code>review.book</code> costs <strong>zero extra queries</strong>.",
        "optimized_code": "Review.objects.select_related('user', 'book')",
    })


def reading_lists(request):
    qs = ReadingList.objects.all()

    unopt = _measure(qs, lambda q: [_reading_list_row(rl) for rl in q[:20]])

    entries_prefetch = Prefetch(
        "entries",
        queryset=ReadingListEntry.objects.select_related("book"),
    )
    opt = _measure(
        qs.select_related("user")
        .prefetch_related(entries_prefetch)
        .annotate(entry_count=Count("entries"))[:20],
        lambda q: [_reading_list_row(rl) for rl in q],
    )

    return render(request, "frontend/compare.html", {
        "title": "Reading Lists",
        "columns": ["Name", "User", "Public?", "Entries", "Books"],
        "unoptimized": unopt,
        "optimized": opt,
        "problem": "Each reading list accesses <code>user</code> (ForeignKey), iterates over <code>entries</code> (reverse FK), and for each entry accesses <code>book</code> (ForeignKey). The entry count also fires a query per list. This creates a cascade: <strong>3N + N×M queries</strong> where N is reading lists and M is entries per list.",
        "unoptimized_code": "ReadingList.objects.all()",
        "fix": "<code>select_related('user')</code> JOINs the user. <code>prefetch_related</code> with a nested <code>select_related('book')</code> fetches entries and their books in just 2 queries. <code>annotate(entry_count=Count('entries'))</code> handles counting in SQL. Total: <strong>2 queries</strong>.",
        "optimized_code": "ReadingList.objects.select_related('user').prefetch_related(\n    Prefetch('entries', queryset=ReadingListEntry.objects.select_related('book')),\n).annotate(entry_count=Count('entries'))",
    })


def borrow_records(request):
    qs = BorrowRecord.objects.all()

    unopt = _measure(qs, lambda q: [_borrow_row(r) for r in q[:20]])

    opt = _measure(
        qs.select_related("user", "book")[:20],
        lambda q: [_borrow_row(r) for r in q],
    )

    return render(request, "frontend/compare.html", {
        "title": "Borrow Records",
        "columns": ["User", "Book", "Borrowed", "Due", "Overdue?"],
        "unoptimized": unopt,
        "optimized": opt,
        "problem": "The template accesses <code>record.user.email</code> and <code>record.book.title</code> — both ForeignKeys. With no optimization, each borrow record fires 2 separate queries to fetch its related user and book. Result: <strong>2N+1 queries</strong>.",
        "unoptimized_code": "BorrowRecord.objects.all()",
        "fix": "<code>select_related('user', 'book')</code> joins all three tables (borrow_records, users, books) in one SQL query. The <code>is_overdue</code> property reads fields already on the model instance — <strong>zero extra queries</strong>.",
        "optimized_code": "BorrowRecord.objects.select_related('user', 'book')",
    })


def users_view(request):
    qs = User.objects.all().order_by("email")

    def _user_row(u):
        return {
            "email": u.email,
            "name": f"{u.first_name} {u.last_name}",
            "reviews": u.reviews.count() if not hasattr(u, "review_count") else u.review_count,
        }

    unopt = _measure(qs[:20], lambda q: [_user_row(u) for u in q])

    opt = _measure(
        qs.annotate(review_count=Count("reviews"))[:20],
        lambda q: [_user_row(u) for u in q],
    )

    return render(request, "frontend/compare.html", {
        "title": "Users",
        "columns": ["Email", "Name", "# Reviews"],
        "unoptimized": unopt,
        "optimized": opt,
        "problem": "The loop calls <code>u.reviews.count()</code> for each user. The <code>reviews</code> relationship is a reverse ForeignKey — Django fires a <code>SELECT COUNT(*)</code> query per user. For N users, you get N extra COUNT queries. Result: <strong>N+1 queries</strong>.",
        "unoptimized_code": "User.objects.all()\n# template calls u.reviews.count() per user",
        "fix": "<code>annotate(review_count=Count('reviews'))</code> adds the count directly into the main SQL query via a <code>COUNT()</code> subquery. The result is available as a plain attribute — <strong>1 query</strong> total.",
        "optimized_code": "User.objects.annotate(review_count=Count('reviews'))",
    })
