# Django Query Optimization Practice

A hands-on project for understanding and teaching how to write faster, more efficient Django ORM queries. Each app in this project exposes pairs of **unoptimized** and **optimized** endpoints so you can see the difference in SQL query counts directly in the response and in the Django Debug Toolbar.

---

## The Problem

Django's ORM makes it dangerously easy to write code that looks innocent but hammers your database. The classic example is the **N+1 problem** — you fetch a list of objects, then for each one Django silently fires another query to fetch a related object. With 1000 users that's 1001 queries for what should be 1.

This project makes that visible and shows you how to fix it.

---

## How This Project Is Structured

Each Django app in this project represents a real-world domain (e.g. users, library). For each resource, there are two endpoints:

- **`/api/<resource>/unoptimized/`** — naive queryset, no prefetching or annotation
- **`/api/<resource>/optimized/`** — tuned queryset using the techniques below

Every response includes a `query_count` field so you can see at a glance how many SQL queries were fired.

---

## Optimization Techniques Covered

### `select_related`
Performs a SQL JOIN to fetch a related object in the same query. Best for `ForeignKey` and `OneToOne` relations.

```python
# Bad — hits the DB once per user to get their profile
users = User.objects.all()
for user in users:
    print(user.profile.bio)  # N extra queries

# Good — single JOIN query
users = User.objects.select_related("profile")
for user in users:
    print(user.profile.bio)  # no extra queries
```

**What Django fires without `select_related`:**

```sql
-- Query 1: fetch users
SELECT * FROM users_user;

-- Query 2..N+1: one per user
SELECT * FROM users_profile WHERE user_id = 1;
SELECT * FROM users_profile WHERE user_id = 2;
-- ... and so on
```

**What Django fires with `select_related`:**

```sql
-- Single query using a JOIN
SELECT users_user.*, users_profile.*
FROM users_user
LEFT OUTER JOIN users_profile ON users_profile.user_id = users_user.id;
```

### `prefetch_related`
Fetches related objects for all rows in one extra query, then maps them in Python. Best for `ManyToMany` and reverse `ForeignKey` relations.

```python
# Bad — hits the DB once per user to get their groups
users = User.objects.all()
for user in users:
    print(user.groups.all())  # N extra queries

# Good — 1 extra query total
users = User.objects.prefetch_related("groups")
for user in users:
    print(user.groups.all())  # no extra queries
```

**What Django fires without `prefetch_related`:**

```sql
-- Query 1: fetch users
SELECT * FROM users_user;

-- Query 2..N+1: one per user
SELECT auth_group.*
FROM auth_group
INNER JOIN users_user_groups ON auth_group.id = users_user_groups.group_id
WHERE users_user_groups.user_id = 1;

SELECT auth_group.*
FROM auth_group
INNER JOIN users_user_groups ON auth_group.id = users_user_groups.group_id
WHERE users_user_groups.user_id = 2;
-- ... and so on
```

**What Django fires with `prefetch_related`:**

```sql
-- Query 1: fetch users
SELECT * FROM users_user;

-- Query 2: fetch ALL groups for ALL users in one go
SELECT auth_group.*, users_user_groups.user_id
FROM auth_group
INNER JOIN users_user_groups ON auth_group.id = users_user_groups.group_id
WHERE users_user_groups.user_id IN (1, 2, 3, ...);
-- Django then maps these to the right users in Python
```

### `annotate`
Computes aggregates (e.g. counts, sums) directly in SQL rather than in Python.

```python
# Bad — Python loop to count
for user in User.objects.all():
    count = user.books.count()  # N extra queries

# Good — COUNT() in the main query
from django.db.models import Count
users = User.objects.annotate(book_count=Count("books"))
for user in users:
    print(user.book_count)  # no extra queries
```

**What Django fires without `annotate`:**

```sql
-- Query 1: fetch users
SELECT * FROM users_user;

-- Query 2..N+1: one COUNT per user
SELECT COUNT(*) FROM library_book WHERE user_id = 1;
SELECT COUNT(*) FROM library_book WHERE user_id = 2;
-- ... and so on
```

**What Django fires with `annotate`:**

```sql
-- Single query — COUNT is computed in the database
SELECT users_user.*, COUNT(library_book.id) AS book_count
FROM users_user
LEFT OUTER JOIN library_book ON library_book.user_id = users_user.id
GROUP BY users_user.id;
```

### `only` / `defer`
Limits the columns fetched from the database to only what you need.

```python
# Fetches every column on the table
User.objects.all()

# Fetches only id, email, first_name
User.objects.only("id", "email", "first_name")
```

**What Django fires without `only`:**

```sql
-- Fetches every column, including ones you never use
SELECT id, email, first_name, last_name, phone, password, is_staff, 
       is_superuser, is_active, date_joined, last_login
FROM users_user;
```

**What Django fires with `only`:**

```sql
-- Fetches only the columns you asked for
SELECT id, email, first_name
FROM users_user;
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

# Create a superuser (to access the browsable API and admin)
uv run manage.py createsuperuser
```

### Seed the Database

```bash
# Seed 1000 users
uv run manage.py seed_users
```

### Run the Dev Server

```bash
uv run manage.py runserver
```

---

## Exploring the API

Once the server is running, open your browser and go to:

- **`http://localhost:8000/api/`** — API root with all available endpoints
- **`http://localhost:8000/api/users/unoptimized/`** — users with N+1 queries
- **`http://localhost:8000/api/users/optimized/`** — users with optimized queries

Log in with the superuser credentials you created. Each response includes a `query_count` field — compare it between the unoptimized and optimized endpoints.

### Django Debug Toolbar

The [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/) is included. It shows you every SQL query fired for a given request, how long each took, and where in your code it came from. Open any endpoint in the browsable API and check the toolbar on the right side of the page.

---

## Apps

### `users`

A custom user model using email as the login field instead of a username. Fields: `first_name`, `last_name`, `email`, `phone`.

Demonstrates: `prefetch_related` on a `ManyToMany` relation.

---

## Contributing

This is a learning project. If you spot something that could be explained better or have an optimization scenario worth adding, open a PR.