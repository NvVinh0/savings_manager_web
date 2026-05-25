from django.db import transaction
from decimal import Decimal
from datetime import date
from django.db.models import Sum
from django.utils.timezone import now

from dashboard.utils import get_parameter
from savings.models import Transaction, Parameter
from django.db.models import QuerySet
from django.utils.timezone import now

from savings.models import SavingPlan, SavingType, SavingTypeRateHistory, Transaction
from users.models import CustomUser

def _add_months(d: date, months: int) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    # keep safe day in target month
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)

def get_all_accounts():
    return SavingPlan.objects.all()

def create_account(
        name: str, citizen_id: str, address: str, balance: Decimal,
        user: CustomUser, saving_type: SavingType
) -> SavingPlan:
    min_initial_deposit = Decimal(get_parameter("min_initial_deposit", 1_000_000))
    if balance < min_initial_deposit:
        raise ValueError(f"Minimum balance is {min_initial_deposit:,.0f}")

    maturity_date = None
    if not saving_type.is_flexible and saving_type.duration_months:
        maturity_date = _add_months(now().date(), saving_type.duration_months)

    account = SavingPlan.objects.create(
        name=name, citizen_id=citizen_id, address=address, balance=balance,
        interest_rate=saving_type.interest_rate,
        # Start accrual tracking on account creation date for flexible accounts.
        interest_last_applied_on=now().date() if saving_type.is_flexible else None,
        maturity_date=maturity_date,
        saving_type=saving_type, user=user)
    return account

def get_account_by_number(account_number: str) -> SavingPlan | None:
    return SavingPlan.objects.get(account_number=account_number)

def get_account_by_user(user: CustomUser) -> QuerySet[SavingPlan, SavingPlan]:
    return SavingPlan.objects.filter(user=user)

# get by name is unreliable
def get_account_by_citizen_id(citizen_id: str) -> QuerySet[SavingPlan, SavingPlan]:
    return SavingPlan.objects.filter(citizen_id=citizen_id)

def deposit_to_account(account: SavingPlan, amount: Decimal):
    minimum_deposit = Decimal(get_parameter("min_additional_deposit", 100_000))
    if amount < minimum_deposit:
        raise ValueError(
            f"Minimum deposit is {minimum_deposit:,.0f}"
        )

    with transaction.atomic():
        account.refresh_from_db()
        today = now().date()

        if not account.saving_type.is_flexible:
            if account.maturity_date is None:
                raise ValueError("Fixed-term account is missing maturity date")
            if today != account.maturity_date:
                raise ValueError("Deposit only allowed on maturity date for fixed-term saving types")
        else:
            # For flexible accounts, accrue pending interest first (using rate history).
            apply_interest(account)
        balance_before = account.balance

        account.balance = balance_before + amount
        account.save(update_fields=["balance"])

        Transaction.objects.create(
            account=account,
            account_number=account.account_number,
            name=account.name,
            transaction_type='DEPOSIT',
            balance_before=balance_before,
            amount=amount,
            balance_after=account.balance
        )

def withdraw_from_account(account: SavingPlan, amount: Decimal) -> Decimal:
    # fixed-term: - only allow withdrawal after maturity day and have to withdraw all balances
    #             - after maturity, interest rate will be non-fixed-term interest rate
    #             - close after withdrawal
    # non-fixed-term: only allow withdrawal after 15 days, can withdraw partial
    # calculate balance after maturity before withdrawal

    with transaction.atomic():
        account.refresh_from_db()
        today = now().date()

        if not account.saving_type.is_flexible: # fixed-term
            if account.maturity_date is None:
                raise ValueError("Fixed-term account is missing maturity date")
            if today < account.maturity_date:
                raise ValueError("Cannot withdraw before maturity")

            # calculate full payout (principal + interest)
            balance = apply_interest(account)

            Transaction.objects.create(
                account=account,
                account_number=account.account_number,
                name=account.name,
                transaction_type='CLOSE',
                balance_before=balance,
                amount=balance, # withdraw all
                balance_after=0
            )

            # close account after withdrawal
            close_account(account)

            return balance
        else:
            # 15-day lock
            days_since_start = (today - account.start_date).days
            if days_since_start < 15:
                raise ValueError("Cannot withdraw within first 15 days")

            balance = apply_interest(account)

            if amount > account.balance:
                raise ValueError("Insufficient balance")

            account.balance = balance - amount
            account.save(update_fields=["balance"])

            Transaction.objects.create(
                account=account,
                account_number=account.account_number,
                name=account.name,
                transaction_type='WITHDRAW',
                balance_before=balance,
                amount=amount,
                balance_after=account.balance
            )

            return amount

def apply_interest(account: SavingPlan):
    # Fixed-term: estimate payout as principal + simple interest.
    if not account.saving_type.is_flexible:
        return account.balance + (account.balance * account.interest_rate / 100)

    today = now().date()
    from_date = account.interest_last_applied_on or account.start_date

    # Nothing to accrue if we've already applied through today.
    if from_date >= today:
        return account.balance

    # Pull all historical rate windows that may overlap the accrual range.
    histories = SavingTypeRateHistory.objects.filter(
        saving_type=account.saving_type,
        effective_from__lt=today
    ).order_by("effective_from")

    interest = Decimal("0")

    if histories.exists():
        for h in histories:
            seg_start = max(from_date, h.effective_from)
            seg_end = min(today, h.effective_to or today)
            if seg_end <= seg_start:
                continue

            days = (seg_end - seg_start).days
            # Simple daily interest, annualized by 365 days.
            interest += account.balance * (h.interest_rate / Decimal("100")) * (Decimal(days) / Decimal("365"))
    else:
        # Backward compatibility when no history rows exist yet.
        days = (today - from_date).days
        interest += account.balance * (account.interest_rate / Decimal("100")) * (Decimal(days) / Decimal("365"))

    account.balance += interest
    account.interest_last_applied_on = today
    # Keep the account snapshot in sync with current saving type display rate.
    account.interest_rate = account.saving_type.interest_rate
    account.save(update_fields=["balance", "interest_last_applied_on", "interest_rate"])
    return account.balance


def change_saving_type_rate(saving_type: SavingType, new_rate: Decimal, effective_from: date | None = None) -> SavingType:
    # Helper to safely change rate while preserving history windows.
    effective_from = effective_from or now().date()

    with transaction.atomic():
        SavingTypeRateHistory.objects.filter(
            saving_type=saving_type,
            effective_to__isnull=True
        ).update(effective_to=effective_from)

        SavingTypeRateHistory.objects.create(
            saving_type=saving_type,
            interest_rate=new_rate,
            effective_from=effective_from,
            effective_to=None
        )

        saving_type.interest_rate = new_rate
        saving_type.save(update_fields=["interest_rate"])

    return saving_type

def close_account(account: SavingPlan):
    return account.delete()

def get_statistics(period: str, saving_plan=None, date=None, month=None, year=None):
    transactions = Transaction.objects.all()

    if saving_plan is not None:
        transactions = transactions.filter(saving_plan=saving_plan)
    
    if period == "day":
        if date:
            transactions = transactions.filter(timestamp__date=date)
    elif period == "month":
        if month:
            try:
                year_val, month_val = month.split("-")
                transactions = transactions.filter(timestamp__year=int(year_val), timestamp__month=int(month_val))
            except ValueError:
                pass
    elif period == "year":
        if year:
            transactions = transactions.filter(timestamp__year=int(year))

    total_open = transactions.filter(transaction_type="OPEN").aggregate(total=Sum("amount"))["total"] or Decimal("0")
    total_deposit = transactions.filter(transaction_type="DEPOSIT").aggregate(total=Sum("amount"))["total"] or Decimal("0")
    total_withdraw = transactions.filter(transaction_type="WITHDRAW").aggregate(total=Sum("amount"))["total"] or Decimal("0")
    total_close = transactions.filter(transaction_type="CLOSE").aggregate(total=Sum("amount"))["total"] or Decimal("0")
    total_income = total_open + total_deposit
    total_expense = total_withdraw + total_close

    if period == "day":
        label = str(date) if date else "N/A"
    elif period == "month":
        label = month if month else "N/A"
    elif period == "year":
        label = str(year) if year else "N/A"
    else:
        label = "N/A"

    return {
        "label": label,
        "account_number": saving_plan.account_number if saving_plan else "All",
        "account_name": getattr(saving_plan, "name", "All accounts") if saving_plan else "All accounts",
        "total_open": total_open,
        "total_deposit": total_deposit,
        "total_withdraw": total_withdraw,
        "total_close": total_close,
        "opened_count": transactions.filter(transaction_type="OPEN").count(),
        "closed_count": transactions.filter(transaction_type="CLOSE").count(),
        "total_income": total_income,
        "total_expense": total_expense,
        "difference": total_income - total_expense
    }
