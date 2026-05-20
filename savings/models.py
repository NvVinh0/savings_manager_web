from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import now
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

    def save(self, *args, **kwargs):
        # Track old rate so we can append a new history row when rate changes.
        old_rate = None
        if self.pk:
            old_rate = SavingType.objects.filter(pk=self.pk).values_list("interest_rate", flat=True).first()

        super().save(*args, **kwargs)

        # Create initial/open history if missing (first save path).
        open_row = self.rate_history.filter(effective_to__isnull=True).order_by("-effective_from").first()
        if open_row is None:
            SavingTypeRateHistory.objects.create(
                saving_type=self,
                interest_rate=self.interest_rate,
                effective_from=now().date(),
                effective_to=None,
            )
            return

        # If rate changed, close current row and open a new one from today.
        if old_rate is not None and old_rate != self.interest_rate:
            today = now().date()
            open_row.effective_to = today
            open_row.save(update_fields=["effective_to"])
            SavingTypeRateHistory.objects.create(
                saving_type=self,
                interest_rate=self.interest_rate,
                effective_from=today,
                effective_to=None,
            )

    def __str__(self):
        return self.name


class SavingTypeRateHistory(models.Model):
    # Keep a timeline of rates so flexible accounts can calculate past periods correctly.
    saving_type = models.ForeignKey(SavingType, on_delete=models.CASCADE, related_name="rate_history")
    interest_rate = models.DecimalField(max_digits=5, decimal_places=4)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)  # null means "still active"

    class Meta:
        ordering = ["effective_from"]

    def __str__(self):
        end = self.effective_to or "present"
        return f"{self.saving_type.name}: {self.interest_rate}% ({self.effective_from} -> {end})"

class SavingAccount(models.Model):
    account_number = models.CharField(
        primary_key=True,
        max_length=10,
        default=generate_account_number,
        editable=False
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    interest_rate = models.DecimalField(max_digits=5, decimal_places=4) # snapshot
    start_date = models.DateField(auto_now_add=True) # lazy evaluation
    maturity_date = models.DateField(null=True, blank=True)  # allow null for non-fixed-term accounts
    # For flexible accounts, this tracks the last day we already accrued interest up to.
    interest_last_applied_on = models.DateField(null=True, blank=True)

    saving_type = models.ForeignKey(SavingType, on_delete=models.PROTECT, related_name="accounts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saving_accounts')

    def deposit(self, amount):
        self.balance += amount
        self.save()

    def withdraw(self, amount):
        if amount > self.balance:
            raise ValueError("Insufficient balance")
        self.balance -= amount
        self.save()

    def delete(self, *args, **kwargs):
        # soft delete the account
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.account_number} - {self.user.full_name}"

class TransactionType(models.TextChoices):
    OPEN = "OPEN", "Account Opening"
    DEPOSIT = "DEPOSIT", "Deposit"
    WITHDRAW = "WITHDRAW", "Withdrawal"
    CLOSE = "CLOSE", "Account Closing"

class Transaction(models.Model):
    transaction_type = models.CharField(max_length=10, choices=TransactionType)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    account = models.ForeignKey(SavingAccount, on_delete=models.PROTECT, related_name='transactions')

    def __str__(self):  
        return f"{self.transaction_type}: {self.amount} on {self.timestamp}"