from django.contrib import admin
from .models import *

@admin.register(SavingType)
class SavingAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_months", "interest_rate", "is_active", "is_flexible")

@admin.register(SavingAccount)
class SavingAdmin(admin.ModelAdmin):
    list_display = ("user", "saving_type", "name", "citizen_id", "address", "balance", "created_at", "interest_rate", "start_date", "maturity_date", "interest_last_applied_on")

@admin.register(SavingTypeRateHistory)
class SavingRateHistoryAdmin(admin.ModelAdmin):
    list_display = ("saving_type", "interest_rate", "effective_from", "effective_to")

@admin.register(Transaction)
class SavingAdmin(admin.ModelAdmin):
    list_display = ("account_number", "name", "transaction_type", "balance_before", "amount", "balance_after", "timestamp")
