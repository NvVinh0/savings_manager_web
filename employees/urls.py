from django.urls import path
from . import views

urlpatterns = [
    path("", views.employee_dashboard, name="employee_dashboard"),
    path("users/", views.manage_users, name="manage_users"),
    path("users/<int:user_id>/", views.manage_user_detail, name="manage_user_profile"),
    path("user_create/", views.user_create, name="user_create"),
    path("savings/", views.manage_saving_plans, name="manage_saving_accounts"),
    path("savings/<str:account_number>/",views.manage_saving_plan_detail,name="manage_saving_plan_detail",),
    path("savings/<str:account_number>/edit/",views.edit_saving_plan,name="edit_saving_plan",),
    path("savings_type/<int:saving_type_id>/edit/",views.edit_saving_type,name="edit_saving_type",),
    path("transactions/", views.manage_transactions, name="manage_transactions"),
    path("reports/", views.manage_reports, name="manage_reports"),
]
