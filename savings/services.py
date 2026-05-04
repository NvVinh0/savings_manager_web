from django.db import transaction
from decimal import Decimal

from django.db.models import QuerySet
from django.utils.timezone import now

from savings.models import SavingAccount, SavingType, Transaction
from users.models import CustomUser

def get_all_accounts():
    return SavingAccount.objects.all()

def create_account(
        name: str, citizen_id: str, address: str, balance: Decimal,
        user: CustomUser, saving_type: SavingType
) -> SavingAccount:
    if balance < 1_000_000:
        raise ValueError("Minimum balance is 1,000,000")

    account = SavingAccount.objects.create(
        name=name, citizen_id=citizen_id, address=address, balance=balance,
        interest_rate=saving_type.interest_rate,
        saving_type=saving_type, user=user)
    return account

def get_account_by_number(account_number: str) -> SavingAccount | None:
    return SavingAccount.objects.get(account_number=account_number)

def get_account_by_user(user: CustomUser) -> QuerySet[SavingAccount, SavingAccount]:
    return SavingAccount.objects.filter(user=user)

# get by name is unreliable
def get_account_by_citizen_id(citizen_id: str) -> QuerySet[SavingAccount, SavingAccount]:
    return SavingAccount.objects.filter(citizen_id=citizen_id)

def deposit_to_account(account: SavingAccount, amount: Decimal):
    # only allow deposit at maturity date (fixed-term only)

    if amount < Decimal("100000"):
        raise ValueError("Minimum deposit is 100,000")

    with transaction.atomic():
        account.refresh_from_db()
        today = now().date()

        if not account.saving_type.is_flexible:
            if today != account.maturity_date:
                raise ValueError("Deposit only allowed on maturity date for fixed-term saving types")
        else:
            apply_interest(account)

        account.balance += amount
        account.save(update_fields=["balance"])

        Transaction.objects.create(
            account=account,
            account_number=account.account_number,
            name=account.name,
            transaction_type='DEPOSIT',
            amount=amount
        )

def withdraw_from_account(account: SavingAccount, amount: Decimal) -> Decimal:
    # fixed-term: - only allow withdrawal after maturity day and have to withdraw all balances
    #             - after maturity, interest rate will be non-fixed-term interest rate
    #             - close after withdrawal
    # non-fixed-term: only allow withdrawal after 15 days, can withdraw partial
    # calculate balance after maturity before withdrawal

    with transaction.atomic():
        account.refresh_from_db()
        today = now().date()

        if not account.saving_type.is_flexible: # fixed-term
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

def apply_interest(account: SavingAccount):
    return account.balance * account.interest_rate / 100 # subjected to change

def close_account(account: SavingAccount):
    return account.delete()