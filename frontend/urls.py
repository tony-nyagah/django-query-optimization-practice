from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("books/", views.books, name="books"),
    path("reviews/", views.reviews, name="reviews"),
    path("reading-lists/", views.reading_lists, name="reading_lists"),
    path("borrow-records/", views.borrow_records, name="borrow_records"),
    path("users/", views.users_view, name="users"),
]
