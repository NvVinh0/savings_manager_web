from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.employee_dashboard, name="employee_dashboard"),
    path("users/", views.manage_users, name="manage_users"),
    path("users/<int:user_id>", views.manage_user_profile, name="manage_user_profile"),
    path("savings/", views.manage_saving_accounts, name="manage_saving_accounts"),
    path("transactions/", views.manage_transactions, name="manage_transactions")
]