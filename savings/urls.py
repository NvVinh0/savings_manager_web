from django.urls import path, include
from . import views

urlpatterns = [
    path("savings/", views.saving_accounts, name="saving_accounts")
]
