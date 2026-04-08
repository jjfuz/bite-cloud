from django.urls import path

from reports import views

urlpatterns = [
    path(
        "financial/<str:scope_type>/<str:scope_id>/",
        views.get_financial_report_view,
        name="get_financial_report",
    ),
    path(
        "orphan-ebs/<str:project_id>/",
        views.get_orphan_ebs_view,
        name="get_orphan_ebs",
    ),
]