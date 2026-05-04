from django.db import models
from django.conf import settings
import random

def generate_account_number():
    """Generates a random 10-digit account number."""
    return "".join([str(random.randint(0, 9)) for _ in range(10)])

class SavingType(models.Model):
    name = models.CharField(max_length=50)
    duration_months = models.IntegerField(null=True, blank=True)  # 3, 6, 12
    interest_rate = models.DecimalField(max_digits=5, decimal_places=4) # 0.05, 0.1, 0.15
    is_active = models.BooleanField(default=True)

    is_flexible = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class SavingAccount(models.Model):
    account_number = models.CharField(
        primary_key=True,
        max_length=10,
        default=generate_account_number,
        editable=False
    )
    name = models.CharField(max_length=50)  # account holder's name'
    citizen_id = models.CharField(max_length=12)
    address = models.CharField(max_length=100)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    interest_rate = models.DecimalField(max_digits=5, decimal_places=4) # snapshot
    start_date = models.DateField(auto_now_add=True) # lazy evaluation
    maturity_date = models.DateField(null=True, blank=True)  # allow null for non-fixed-term accounts

    saving_type = models.ForeignKey(SavingType, on_delete=models.PROTECT, related_name="accounts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='saving_accounts')

    def deposit(self, amount):
        self.balance += amount
        self.save()

    def withdraw(self, amount):
        if amount > self.balance:
            raise ValueError("Insufficient balance")
        self.balance -= amount
        self.save()

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('OPEN', 'Account Opening'),
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAW', 'Withdrawal'),
        ('CLOSE', 'Account Closing'),
    ]

    account_number = models.CharField(max_length=10)
    name = models.CharField(max_length=50)  # transaction maker's name
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    account = models.ForeignKey(SavingAccount, on_delete=models.SET_NULL, related_name='transactions')

    def __str__(self):
        return f"{self.transaction_type}: {self.amount} on {self.timestamp}"
