from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.saving_plans, name="saving_plans"),
    path("<str:plan_id>/", views.saving_plan_detail, name="saving_plan_detail"),
    path("create/", views.saving_plan_create, name="saving_plan_create"),
]
