import debug_toolbar
from django.contrib import admin
from django.urls import include, path
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView


class APIRootView(APIView):
    """
    # Django Query Optimization Practice

    Welcome! This API exposes endpoints that demonstrate optimized and
    unoptimized Django ORM queries.

    Browse the available endpoints below.
    """

    def get(self, request):
        return Response(
            {
                "users": reverse("users-list", request=request),
                "books": {
                    "unoptimized": reverse("unoptimized-books-list", request=request),
                    "optimized": reverse("optimized-books-list", request=request),
                },
                "reviews": {
                    "unoptimized": reverse("unoptimized-reviews-list", request=request),
                    "optimized": reverse("optimized-reviews-list", request=request),
                },
                "reading_lists": {
                    "unoptimized": reverse(
                        "unoptimized-reading-lists-list", request=request
                    ),
                    "optimized": reverse(
                        "optimized-reading-lists-list", request=request
                    ),
                },
                "borrow_records": {
                    "unoptimized": reverse(
                        "unoptimized-borrow-records-list", request=request
                    ),
                    "optimized": reverse(
                        "optimized-borrow-records-list", request=request
                    ),
                },
            }
        )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("__debug__/", include(debug_toolbar.urls)),
    path("api/", APIRootView.as_view(), name="api-root"),
    path("api/", include("users.urls")),
    path("api/", include("books.urls")),
    path("api/", include("library.urls")),
    path("api-auth/", include("rest_framework.urls")),
]
