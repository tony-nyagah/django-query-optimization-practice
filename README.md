# Django Query Optimization

Hands-on demo of the **N+1 query problem** and how to fix it with Django's ORM.

Open `https://django-query-optimization.nyagah.me` and click through — each page runs an unoptimized query against an optimized one side by side, showing exact query counts and timing.

## Quick start

```bash
uv sync
mkdir -p data
uv run manage.py migrate
uv run manage.py seed_users    # 1000 users
uv run manage.py seed_books    # 5000 books, 300 authors, 100 publishers
uv run manage.py seed_library  # reviews, reading lists, borrow records
uv run manage.py runserver
```

Open `http://localhost:8000`.

## Techniques demonstrated

| Technique | What it does | Used in |
|-----------|-------------|---------|
| `select_related` | SQL JOIN on ForeignKeys | Reviews, Borrows, Books |
| `prefetch_related` | Batched fetch for M2M / reverse FK | Books, Reading Lists |
| `annotate` | Compute aggregates in SQL | Books, Reading Lists, Users |
| `only` / `defer` | Limit columns fetched | Books |

## API

The REST API is at `/api/` with optimized and unoptimized variants for each resource. Requires auth (session or token). Browse `/api/` for the full root.

## Project structure

- **`books`** — Book, Author, Genre, Publisher (M2M through tables)
- **`library`** — Review, ReadingList, ReadingListEntry, BorrowRecord
- **`users`** — Custom user model (email login)
- **`frontend`** — Django templates that measure and compare queries

## Deployment

Docker image builds via GitHub Actions (`ghcr.io/tony-nyagah/django-query-optimization-practice`). Deployed through the [infra](https://github.com/tony-nyagah/infra) repo alongside other projects.
