# Django Query Optimization Practice

A hands-on project for understanding and teaching how to write faster, more efficient Django ORM queries. Each app exposes pairs of **unoptimized** and **optimized** endpoints so you can see the difference in SQL query counts directly in the Django Debug Toolbar.

---

## The Problem

Django's ORM makes it dangerously easy to write code that looks innocent but hammers your database. The classic example is the **N+1 problem** — you fetch a list of objects, then for each one Django silently fires another query to fetch a related object. With 1000 users that's 1001 queries for what should be 1.

This project makes that visible and shows you exactly how to fix it.

---

## How This Project Is Structured

There are three Django apps, each representing a real-world domain:

- **`users`** — custom user model with email-based login
- **`books`** — books, authors, genres, and publishers
- **`library`** — reviews, reading lists, and borrow records

For each resource there are two endpoints:

- **`/api/<resource>/unoptimized/`** — naive queryset, no prefetching or annotation
- **`/api/<resource>/optimized/`** — tuned queryset using the techniques below

Open both side by side in the Django Debug Toolbar and compare the query counts.

---

## Optimization Techniques Covered

### `select_related`

Performs a SQL JOIN to fetch a related object in the same query. Best for `ForeignKey` and `OneToOne` relations.

```python
# Bad — hits the DB once per review to get the user and book
reviews = Review.objects.all()
for review in reviews:
    print(review.user.email)   # N extra queries
    print(review.book.title)   # N extra queries

# Good — single JOIN query fetches everything
reviews = Review.objects.select_related("user", "book")
for review in reviews:
    print(review.user.email)   # no extra queries
    print(review.book.title)   # no extra queries
```

**Without `select_related`:**

```sql
-- Query 1: fetch reviews
SELECT * FROM library_review;

-- Query 2..N+1: one per review for the user
SELECT * FROM users_user WHERE id = 1;
SELECT * FROM users_user WHERE id = 2;
-- ... and so on

-- Query N+2..2N+1: one per review for the book
SELECT * FROM books_book WHERE id = 1;
SELECT * FROM books_book WHERE id = 2;
-- ... and so on
```

**With `select_related`:**

```sql
-- Single query — all three tables JOINed together
SELECT library_review.*, users_user.*, books_book.*
FROM library_review
INNER JOIN users_user ON users_user.id = library_review.user_id
INNER JOIN books_book ON books_book.id = library_review.book_id;
```

---

### `prefetch_related`

Fetches related objects for all rows in one extra query, then maps them in Python. Best for `ManyToMany` and reverse `ForeignKey` relations.

```python
# Bad — hits the DB once per book to get authors and genres
books = Book.objects.all()
for book in books:
    print(book.authors.all())  # N extra queries
    print(book.genres.all())   # N extra queries

# Good — 2 extra queries total regardless of N
books = Book.objects.prefetch_related("authors", "genres")
for book in books:
    print(book.authors.all())  # no extra queries
    print(book.genres.all())   # no extra queries
```

**Without `prefetch_related`:**

```sql
-- Query 1: fetch books
SELECT * FROM books_book;

-- Query 2..N+1: one per book for authors
SELECT books_author.*
FROM books_author
INNER JOIN books_bookauthor ON books_author.id = books_bookauthor.author_id
WHERE books_bookauthor.book_id = 1;
-- ... and so on

-- Query N+2..2N+1: one per book for genres
SELECT books_genre.*
FROM books_genre
INNER JOIN books_bookgenre ON books_genre.id = books_bookgenre.genre_id
WHERE books_bookgenre.book_id = 1;
-- ... and so on
```

**With `prefetch_related`:**

```sql
-- Query 1: fetch books
SELECT * FROM books_book;

-- Query 2: fetch ALL authors for ALL books in one go
SELECT books_author.*, books_bookauthor.book_id
FROM books_author
INNER JOIN books_bookauthor ON books_author.id = books_bookauthor.author_id
WHERE books_bookauthor.book_id IN (1, 2, 3, ...);

-- Query 3: fetch ALL genres for ALL books in one go
SELECT books_genre.*, books_bookgenre.book_id
FROM books_genre
INNER JOIN books_bookgenre ON books_genre.id = books_bookgenre.genre_id
WHERE books_bookgenre.book_id IN (1, 2, 3, ...);
```

---

### `annotate`

Computes aggregates (e.g. counts, sums) directly in SQL rather than in Python.

```python
# Bad — hits the DB once per book to count its authors
for book in Book.objects.all():
    print(book.authors.count())  # N extra queries

# Good — COUNT() computed in the main query
from django.db.models import Count
books = Book.objects.annotate(author_count=Count("authors"))
for book in books:
    print(book.author_count)  # no extra queries
```

**Without `annotate`:**

```sql
-- Query 1: fetch books
SELECT * FROM books_book;

-- Query 2..N+1: one COUNT per book
SELECT COUNT(*) FROM books_bookauthor WHERE book_id = 1;
SELECT COUNT(*) FROM books_bookauthor WHERE book_id = 2;
-- ... and so on
```

**With `annotate`:**

```sql
-- Single query — COUNT computed in the database
SELECT books_book.*, COUNT(books_bookauthor.id) AS author_count
FROM books_book
LEFT OUTER JOIN books_bookauthor ON books_bookauthor.book_id = books_book.id
GROUP BY books_book.id;
```

---

### `only` / `defer`

Limits the columns fetched from the database to only what you need.

```python
# Fetches every column on the table
Book.objects.all()

# Fetches only the columns the serializer actually uses
Book.objects.only("id", "title", "isbn", "published_date", "page_count", "language", "average_rating")
```

**Without `only`:**

```sql
-- Fetches every column, including ones you never use
SELECT id, title, isbn, publisher_id, published_date, page_count,
       cover_image_url, language, average_rating
FROM books_book;
```

**With `only`:**

```sql
-- Fetches only the columns you asked for
SELECT id, title, isbn, published_date, page_count, language, average_rating
FROM books_book;
```

---

## Getting Started

### Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)

### Setup

```bash
# Install dependencies
uv sync

# Run migrations
uv run manage.py migrate

# Create a superuser to access the browsable API and admin
uv run manage.py createsuperuser
```

### Seed the Database

Run the seed commands in this order:

```bash
# 1. Seed books, authors, genres, and publishers
#    (300 authors, 100 publishers, 20 genres, 5000 books)
uv run manage.py seed_books

# 2. Seed 1000 users
uv run manage.py seed_users

# 3. Seed library data (reviews, reading lists, borrow records)
uv run manage.py seed_library
```

### Run the Dev Server

```bash
uv run manage.py runserver
```

---

## Exploring the API

Once the server is running visit `http://localhost:8000/api/` for the full API root.

Log in with your superuser credentials. Then open the unoptimized and optimized versions of each endpoint side by side and watch the Django Debug Toolbar.

### Users

| Endpoint | Description |
|---|---|
| `GET /api/users/` | List all users |
| `GET /api/users/{id}/` | Retrieve a single user |

### Books

| Endpoint | Technique | Description |
|---|---|---|
| `GET /api/books/unoptimized/` | — | N+1 on publisher, authors, genres, and author count |
| `GET /api/books/optimized/` | `select_related`, `prefetch_related`, `annotate`, `only` | 3 queries regardless of page size |

### Reviews

| Endpoint | Technique | Description |
|---|---|---|
| `GET /api/reviews/unoptimized/` | — | N+1 on user and book per review |
| `GET /api/reviews/optimized/` | `select_related` | 1 query regardless of page size |

### Reading Lists

| Endpoint | Technique | Description |
|---|---|---|
| `GET /api/reading-lists/unoptimized/` | — | N+1 on user, entries, and each entry's book |
| `GET /api/reading-lists/optimized/` | `select_related`, `prefetch_related`, `annotate` | 2 queries regardless of page size |

### Borrow Records

| Endpoint | Technique | Description |
|---|---|---|
| `GET /api/borrow-records/unoptimized/` | — | N+1 on user and book per record |
| `GET /api/borrow-records/optimized/` | `select_related` | 1 query regardless of page size |

---

### Django Debug Toolbar

The [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/) is enabled in development. It shows every SQL query fired for a given request, how long each took, and the exact line of code that triggered it. Open any endpoint in the browsable API and check the toolbar panel on the right.

---

## Apps

### `users`

Custom user model using email as the login field. Fields: `first_name`, `last_name`, `email`, `phone`.

### `books`

Models: `Book`, `Author`, `Genre`, `Publisher`, `BookAuthor` (through), `BookGenre` (through).

Demonstrates: `select_related` on a `ForeignKey` (publisher), `prefetch_related` on two `ManyToMany` relations (authors, genres), `annotate` for author count, and `only` to limit fetched columns.

### `library`

Models: `Review`, `ReadingList`, `ReadingListEntry`, `BorrowRecord`.

Demonstrates: `select_related` on multiple `ForeignKey` relations, `prefetch_related` with a nested `select_related` via `Prefetch`, and `annotate` for entry counts.

---

## Contributing

This is a learning project. If you spot something that could be explained better or have an optimization scenario worth adding, open a PR.