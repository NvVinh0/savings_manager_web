from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.employee_dashboard, name="employee_dashboard"),
    path("users/", views.manage_users, name="manage_users"),
    path("savings/", views.manage_saving_accounts, name="manage_saving_accounts"),
    path("transactions/", views.manage_transactions, name="manage_transactions")
]