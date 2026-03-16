# Your Django App Is Making Way Too Many Database Calls (Here's How to Fix It)

A while back I was debugging a slow API at work. The endpoint wasn't doing anything crazy — just fetching a list of records and returning some related data alongside them. But it was *slow*. Noticeably, embarrassingly slow.

I opened up Django Debug Toolbar, looked at the SQL panel, and felt my stomach drop.

**Thousands of queries. For a single request.**

The code looked completely fine. There was no obvious loop hammering the database, no rogue recursive function. Just a clean-looking queryset and a serializer. And yet Django was quietly firing hundreds of duplicate database calls behind the scenes — doing in thousands of queries what should have taken five.

That was the day I truly understood the N+1 problem. And once you see it, you can't unsee it.

This article walks you through what it is, why Django makes it so easy to fall into, and the four techniques that will fix it. I also built a hands-on companion project you can clone and run yourself so you can see the query counts drop in real time:

**[github.com/tony-nyagah/django-query-optimization-practice](https://github.com/tony-nyagah/django-query-optimization-practice)**

---

## What Is the N+1 Problem?

The N+1 problem happens when you fetch a list of N objects and then, for each one, fire a separate query to fetch a related object. That's N extra queries on top of the original 1 — hence N+1.

Here's the simplest possible example. Say you have a `Review` model with a foreign key to both a `User` and a `Book`:

```django-query-optimization-practice/library/models.py#L1-L22
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
    rating = models.PositiveSmallIntegerField()
    body = models.TextField(blank=True)
    is_spoiler = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

And a serializer that reads `review.user.email` and `review.book.title`:

```django-query-optimization-practice/library/serializers.py#L1-L18
from rest_framework import serializers
from .models import Review


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
```

Now in your view, you write what looks like a perfectly innocent queryset:

```django-query-optimization-practice/library/views.py#L22-L27
class UnoptimizedReviewViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        return Review.objects.all()
```

Looks fine, right? But here's what Django actually does when you hit that endpoint with, say, 100 reviews on the page:

- **1 query** to fetch the reviews
- **100 queries** to fetch each review's user (one per row)
- **100 queries** to fetch each review's book (one per row)

**Total: 201 queries.** For one request. And every single "extra" query is fetching data you've already fetched for a previous row.

Scale that up to a real dataset — thousands of reviews, a busy API — and you have a serious problem.

---

## Making It Visible

Before we fix anything, you need to be able to *see* the problem. That's where [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/) comes in.

With Debug Toolbar installed, every request in your browser shows a panel on the right side of the screen with:

- The total number of SQL queries fired
- The exact SQL for each one
- How long each query took
- The line of Python code that triggered it

When you open an unoptimized endpoint, you'll see the same pattern repeated hundreds of times:

```/dev/null/sql-example.sql#L1-L8
SELECT * FROM users_user WHERE id = 1;
SELECT * FROM users_user WHERE id = 2;
SELECT * FROM users_user WHERE id = 3;
-- ... 97 more of these
SELECT * FROM books_book WHERE id = 1;
SELECT * FROM books_book WHERE id = 2;
-- ... 99 more of these
```

That's your N+1. Now let's fix it.

---

## The Fixes

There are four main tools in Django's ORM for dealing with this. Each one solves a slightly different flavour of the problem.

### 1. `select_related` — for ForeignKey and OneToOne relations

`select_related` tells Django to perform a SQL JOIN and fetch the related object in the same query. Instead of 1 + N queries, you get 1 query total.

```django-query-optimization-practice/library/views.py#L38-L52
class OptimizedReviewViewSet(viewsets.ReadOnlyModelViewSet):
    """
    select_related('user', 'book') performs a single SQL JOIN across
    reviews, users, and books so all three are fetched in one query.
    Accessing review.user or review.book costs zero extra queries.

    Total: 1 query regardless of N.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        return Review.objects.select_related("user", "book")
```

The SQL Django generates looks like this:

```/dev/null/sql-select-related.sql#L1-L5
SELECT library_review.*, users_user.*, books_book.*
FROM library_review
INNER JOIN users_user ON users_user.id = library_review.user_id
INNER JOIN books_book ON books_book.id = library_review.book_id;
```

One query. Everything fetched. Done.

**Rule of thumb:** use `select_related` any time you're traversing a `ForeignKey` or `OneToOne` field. It's almost always the right call.

---

### 2. `prefetch_related` — for ManyToMany and reverse ForeignKey relations

`select_related` uses SQL JOINs, which work great for single related objects. But for `ManyToMany` relations or reverse foreign keys (where one object can have many related objects), JOINs get messy and can multiply your rows. That's where `prefetch_related` comes in.

Instead of a JOIN, Django fires one additional query to fetch all related objects for all rows at once, then maps everything together in Python.

Here's a `Book` model that has `ManyToMany` relations to both `Author` and `Genre`:

```django-query-optimization-practice/books/models.py#L33-L55
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
```

The unoptimized view just returns `Book.objects.all()`. For a page of N books with authors and genres, that's `4N + 1` queries. On a page of 50 books, that's **201 queries**.

The optimized view uses `prefetch_related` to fetch all authors and genres in bulk:

```django-query-optimization-practice/books/views.py#L50-L85
class OptimizedBookViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OptimizedBookSerializer

    def get_queryset(self):
        book_authors_prefetch = Prefetch(
            "book_authors",
            queryset=BookAuthor.objects.select_related("author"),
        )

        return (
            Book.objects.select_related("publisher")
            .prefetch_related(book_authors_prefetch, "genres")
            .annotate(author_count=Count("authors"))
            .only(
                "id",
                "title",
                "isbn",
                "publisher",
                "published_date",
                "page_count",
                "language",
                "average_rating",
            )
        )
```

Notice the `Prefetch` object being used for `book_authors`. This is a more powerful version of `prefetch_related` that lets you supply a custom queryset — in this case, one that also does a `select_related("author")` to grab the author details in the same prefetch query, rather than firing yet another query per author.

The SQL goes from hundreds of small queries to just three:

```/dev/null/sql-prefetch.sql#L1-L14
-- Query 1: fetch books (with publisher JOINed in)
SELECT books_book.*, books_publisher.*
FROM books_book
LEFT OUTER JOIN books_publisher ON books_publisher.id = books_book.publisher_id;

-- Query 2: fetch ALL book_authors + their authors in one go
SELECT books_bookauthor.*, books_author.*
FROM books_bookauthor
INNER JOIN books_author ON books_author.id = books_bookauthor.author_id
WHERE books_bookauthor.book_id IN (1, 2, 3, ...);

-- Query 3: fetch ALL genres for ALL books in one go
SELECT books_genre.*, books_bookgenre.book_id
FROM books_genre
INNER JOIN books_bookgenre ON books_genre.id = books_bookgenre.book_id
WHERE books_bookgenre.book_id IN (1, 2, 3, ...);
```

**3 queries. Regardless of page size.**

**Rule of thumb:** use `prefetch_related` for `ManyToMany` fields and reverse `ForeignKey` relations (i.e. accessing the "many" side). Use the `Prefetch` object when you need to apply filtering, ordering, or chained `select_related` on the prefetched queryset.

---

### 3. `annotate` — push aggregates into SQL instead of computing them in Python

This one catches a lot of people off guard. Say your serializer needs to show how many authors a book has. The tempting approach is:

```/dev/null/naive-count.py#L1-L3
def get_author_count(self, obj):
    return obj.authors.count()  # fires a new COUNT query for every single book
```

That `count()` call hits the database once per book. With 50 books on the page, that's 50 extra queries.

The fix is `annotate`. It pushes the `COUNT` into the main SQL query so it's computed in the database — no extra queries at all:

```/dev/null/annotate-example.py#L1-L4
from django.db.models import Count

Book.objects.annotate(author_count=Count("authors"))
# book.author_count is now a plain integer — no query needed
```

In the optimized serializer, `author_count` is declared as a plain `IntegerField` instead of a `SerializerMethodField`, because the value is already there on the object:

```django-query-optimization-practice/books/serializers.py#L59-L63
class OptimizedBookSerializer(serializers.ModelSerializer):
    publisher = PublisherSerializer()
    authors = BookAuthorSerializer(source="book_authors", many=True)
    genres = GenreSerializer(many=True)
    author_count = serializers.IntegerField()
```

That's the key difference between the two serializers — the unoptimized one calls `obj.authors.count()` which fires a query, and the optimized one just reads `obj.author_count` which is already an integer baked into the queryset result.

**Rule of thumb:** any time you find yourself calling `.count()`, `.sum()`, `.avg()`, or similar inside a loop or a `SerializerMethodField`, stop and use `annotate` instead.

---

### 4. `only` — fetch just the columns you actually need

This one is more subtle but still worth knowing. By default, `Book.objects.all()` fetches every column in the `books_book` table — including ones your serializer never touches. With wide tables, that's wasted data moving over the wire on every request.

`only()` limits the `SELECT` to specific columns:

```/dev/null/only-example.py#L1-L10
# Without only — fetches every column, including ones you never use
Book.objects.all()
# SELECT id, title, isbn, publisher_id, published_date, page_count,
#        cover_image_url, language, average_rating FROM books_book;

# With only — fetches exactly what the serializer needs
Book.objects.only("id", "title", "isbn", "publisher", "published_date", "page_count", "language", "average_rating")
# SELECT id, title, isbn, publisher_id, published_date, page_count,
#        language, average_rating FROM books_book;
```

One important gotcha: if you later access a field that wasn't in your `only()` list, Django will fire a *deferred* query to fetch it. So make sure your `only()` list matches exactly what your serializer uses. A good habit is to write `only()` last, after you've finalized your serializer fields.

---

## The ReadingList: All Four Techniques Together

The reading list is the most complex case in the companion project and a good example of how these techniques stack. A `ReadingList` has a user (FK), a list of `ReadingListEntry` objects (reverse FK), and each entry has a book (FK). Unoptimized, the query count for a page of N reading lists with M entries each is:

```
1 query           — fetch reading lists
N queries         — fetch each list's user
N queries         — fetch each list's entries
N * M queries     — fetch each entry's book
N queries         — count each list's entries
─────────────────────────────────────
3N + (N * M) + 1 queries total
```

With 20 reading lists of 10 entries each, that's **221 queries**.

The optimized view brings it down to 2:

```django-query-optimization-practice/library/views.py#L80-L107
class OptimizedReadingListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    1. select_related('user')
       JOINs users into the main query — zero extra queries for user access.

    2. prefetch_related(Prefetch('entries', queryset=...select_related('book')))
       Fetches all entries for all reading lists in one query, with their
       books JOINed in. Accessing entries and their books costs zero extra
       queries.

    3. annotate(entry_count=Count('entries'))
       Computes the entry count per list in SQL — zero extra queries.

    Total: 2 queries regardless of N.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ReadingListSerializer

    def get_queryset(self):
        entries_prefetch = Prefetch(
            "entries",
            queryset=ReadingListEntry.objects.select_related("book"),
        )

        return (
            ReadingList.objects.select_related("user")
            .prefetch_related(entries_prefetch)
            .annotate(entry_count=Count("entries"))
        )
```

That's `select_related` for the user, a nested `Prefetch` with `select_related` for the entries and their books, and `annotate` for the count. 221 queries → 2.

---

## Try It Yourself

The companion project is set up so you can see all of this live in your browser. Clone it, seed the database, run the server, and open the Debug Toolbar on both versions of each endpoint side by side.

```/dev/null/setup.sh#L1-L14
# Clone the repo
git clone https://github.com/tony-nyagah/django-query-optimization-practice
cd django-query-optimization-practice

# Install dependencies (requires uv)
uv sync

# Run migrations
uv run manage.py migrate

# Seed the database
uv run manage.py seed_books   # 5000 books, 300 authors, 100 publishers, 20 genres
uv run manage.py seed_users   # 1000 users
uv run manage.py seed_library # reviews, reading lists, borrow records

# Run the server
uv run manage.py runserver
```

Then visit `http://localhost:8000/api/` and explore the endpoints. The Debug Toolbar is already wired up. Compare `/api/books/unoptimized/` against `/api/books/optimized/` and watch the query count go from 4N+1 to 3.

---

## Quick Reference

Here's a cheat sheet for when to reach for each technique:

| Situation | Tool |
|---|---|
| Accessing a `ForeignKey` or `OneToOne` field | `select_related` |
| Accessing a `ManyToMany` or reverse FK | `prefetch_related` |
| Need to filter/order the prefetched queryset | `Prefetch` object |
| Calling `.count()`, `.sum()`, etc. per object | `annotate` |
| Wide table, serializer only needs a few columns | `only` |

---

## The Mindset Shift

The real lesson here isn't memorizing which method to use. It's learning to *think about what SQL your code is generating*.

Django's ORM is a fantastic abstraction — it lets you write clean, readable Python and not think about SQL 90% of the time. But that abstraction can hide a lot of expensive mistakes. The N+1 problem is the most common, but it's really just a symptom of not thinking about what's happening at the database level.

Get in the habit of:
- Checking the Debug Toolbar (or logging SQL queries) during development
- Looking at your views and asking "what related data does my serializer need, and am I fetching it upfront?"
- Treating `select_related` and `prefetch_related` as the default for any queryset that touches related data, not an afterthought

Once you build that habit, you stop writing N+1 bugs in the first place. And you stop staring at a toolbar showing 2,000 queries wondering where it all went wrong.

---

*Antony Nyagah is a software engineer who enjoys building things and occasionally debugging the choices past-him made. The companion project for this article is at [github.com/tony-nyagah/django-query-optimization-practice](https://github.com/tony-nyagah/django-query-optimization-practice).*