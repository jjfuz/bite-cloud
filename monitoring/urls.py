from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", views.health, name="health"),
    path("reports/", include("reports.urls")),
]