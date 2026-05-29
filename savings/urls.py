from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.saving_plans, name="saving_plans"),
    path("types/", views.saving_types, name="saving_types"),
    path("<str:plan_id>/", views.saving_plan_detail, name="saving_plan_detail"),
]
