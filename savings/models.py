from django.db import models
from django.utils import timezone
from django.utils.timezone import now
import random

from users.models import Customer

def generate_plan_id():
    """Generates a random 10-digit saving plan ID."""
    return "".join([str(random.randint(0, 9)) for _ in range(10)])


class SavingType(models.Model):
    name = models.CharField(max_length=50)
    duration_months = models.IntegerField(null=True, blank=True)  # 3, 6, 12
    interest_rate = models.DecimalField(max_digits=5, decimal_places=4) # 0.05, 0.1, 0.15
    is_flexible = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

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

class SavingTypeRateHistory(models.Model):
    # Keep a timeline of rates so flexible saving plans can calculate past periods correctly.
    saving_type = models.ForeignKey(SavingType, on_delete=models.CASCADE, related_name="rate_history")
    interest_rate = models.DecimalField(max_digits=5, decimal_places=4)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)  # null means "still active"

    class Meta:
        ordering = ["effective_from"]

class SavingPlanStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACTIVE = "ACTIVE", "Active"
    CLOSED = "CLOSED", "Closed"

class SavingPlan(models.Model):
    plan_id = models.CharField(
        primary_key=True,
        max_length=10,
        default=generate_plan_id,
        editable=False
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=10, choices=SavingPlanStatus, default=SavingPlanStatus.PENDING)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    interest_rate = models.DecimalField(max_digits=5, decimal_places=4) # snapshot
    start_date = models.DateField(null=True) # lazy evaluation
    maturity_date = models.DateField(null=True, blank=True)  # allow null for non-fixed-term saving plans
    # For flexible saving plans, this tracks the last day we already accrued interest up to.
    interest_last_applied_on = models.DateField(null=True, blank=True)

    saving_type = models.ForeignKey(SavingType, on_delete=models.PROTECT, related_name="saving_plans")
    customer = models.ForeignKey(Customer, null=True, on_delete=models.SET_NULL, related_name='saving_plans')

    def deposit(self, amount):
        self.balance += amount
        self.save()

    def withdraw(self, amount):
        if amount > self.balance:
            raise ValueError("Insufficient balance")
        self.balance -= amount
        self.save()

    def update_status(self):
        if self.status == SavingPlanStatus.PENDING:
            self.status = SavingPlanStatus.ACTIVE
            self.start_date = now().date()
            self.save(update_fields=["status", "start_date"])

    def soft_delete(self):
        if self.status == SavingPlanStatus.ACTIVE:
            self.status = SavingPlanStatus.CLOSED
            self.deactivated_at = timezone.now()
            self.save(update_fields=["status", "deactivated_at"])

class TransactionType(models.TextChoices):
    OPEN = "OPEN", "Saving Plan Opening"
    DEPOSIT = "DEPOSIT", "Deposit"
    WITHDRAW = "WITHDRAW", "Withdrawal"
    CLOSE = "CLOSE", "Saving Plan Closing"

class TransactionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SUCCESS = "SUCCESS", "Success"
    CANCELED = "CANCELED", "Canceled"

class Transaction(models.Model):
    transaction_type = models.CharField(max_length=10, choices=TransactionType)
    transaction_status = models.CharField(max_length=10, choices=TransactionStatus)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    saving_plan = models.ForeignKey(SavingPlan, on_delete=models.PROTECT, related_name='transactions')

    def update_status(self, is_success: bool = False):
        if self.transaction_status == TransactionStatus.CANCELED:
            return

        if self.transaction_status == TransactionStatus.PENDING:
            self.transaction_status = TransactionStatus.SUCCESS if is_success else TransactionStatus.CANCELED
        else:
            self.transaction_status = TransactionStatus.PENDING
        self.save()


class Parameter(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=255)
