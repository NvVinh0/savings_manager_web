from django.contrib import admin
from .models import *

@admin.register(SavingType)
class SavingAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_months", "interest_rate", "is_active", "is_flexible")

@admin.register(SavingAccount)
class SavingAdmin(admin.ModelAdmin):
    list_display = ("saving_type", "balance", "created_at", "interest_rate", "start_date", "maturity_date", "interest_last_applied_on")
    list_select_related = ("user", "saving_type")

@admin.register(SavingTypeRateHistory)
class SavingRateHistoryAdmin(admin.ModelAdmin):
    list_display = ("saving_type", "interest_rate", "effective_from", "effective_to")

@admin.register(Transaction)
class SavingAdmin(admin.ModelAdmin):
    list_display = ("transaction_type", "balance_before", "amount", "balance_after", "timestamp")
    list_select_related = ("account", "user")
