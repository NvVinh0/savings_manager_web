from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.saving_plans, name="saving_plans"),
    path("create/", views.saving_plan_create, name="saving_plan_create"),
    path("<str:plan_id>/", views.saving_plan_detail, name="saving_plan_detail"),
    path("transactions/<int:transaction_id>/approve/", views.employee_approve_transaction, name="employee_approve_transaction"),
    path("transactions/<int:transaction_id>/reject/", views.employee_reject_transaction, name="employee_reject_transaction"),
]
