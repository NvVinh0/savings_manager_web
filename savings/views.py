from decimal import Decimal

from django.contrib import messages
from django.shortcuts import redirect, render

from dashboard.decorators import customer_required
from savings.forms import (
    CreateSavingAccountForm,
    DepositForm,
    WithdrawForm,
    ReportForm,
)

from savings.models import SavingType

from savings.services import (
    create_account,
    deposit_to_account,
    get_account_by_user,
    withdraw_from_account,
    get_statistics,
)


@customer_required
def saving_accounts(request):
    accounts = get_account_by_user(request.user)
    saving_types = SavingType.objects.filter(is_active=True).order_by("name")
    create_form = CreateSavingAccountForm(prefix="create")
    deposit_form = DepositForm(prefix="deposit", accounts_qs=accounts)
    withdraw_form = WithdrawForm(prefix="withdraw", accounts_qs=accounts)

    report_form = ReportForm(accounts_qs=accounts)
    statistics = None

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        try:
            if form_type == "create":
                create_form = CreateSavingAccountForm(request.POST, prefix="create")

                if create_form.is_valid():
                    create_account(
                        name=create_form.cleaned_data["name"],
                        citizen_id=create_form.cleaned_data["citizen_id"],
                        address=create_form.cleaned_data["address"],
                        balance=create_form.cleaned_data["balance"],
                        user=request.user,
                        saving_type=create_form.cleaned_data["saving_type"],
                    )
                    messages.success(request, "Saving account created successfully.")
                    return redirect("saving_accounts")

            elif form_type == "deposit":
                deposit_form = DepositForm(request.POST, prefix="deposit", accounts_qs=accounts)

                if deposit_form.is_valid():
                    account = deposit_form.cleaned_data["account"]
                    deposit_to_account(account, deposit_form.cleaned_data["amount"])
                    messages.success(request, "Deposit completed.")
                    return redirect("saving_accounts")

            elif form_type == "withdraw":
                withdraw_form = WithdrawForm(request.POST, prefix="withdraw", accounts_qs=accounts)

                if withdraw_form.is_valid():
                    account = withdraw_form.cleaned_data["account"]
                    amount = withdraw_form.cleaned_data.get("amount")

                    withdraw_from_account(
                        account,
                        amount if amount is not None else Decimal("0")
                    )

                    messages.success(request, "Withdrawal completed.")
                    return redirect("saving_accounts")

            elif form_type == "statistics":

                report_form = ReportForm(request.POST, accounts_qs=accounts)

                if report_form.is_valid():

                    period_type = report_form.cleaned_data["period_type"]
                    account = report_form.cleaned_data["account"]
                    date = report_form.cleaned_data.get("date")

                    month = request.POST.get("month")
                    year = request.POST.get("year")

                    statistics = get_statistics(
                        period_type,
                        date,
                        account,
                        month,
                        year
                    )

                    messages.success(request, "Report generated successfully.")

        except ValueError as exc:
            messages.error(request, str(exc))

    return render(
        request,
        "savings/saving_accounts.html",
        {
            "accounts": accounts,
            "saving_types": saving_types,
            "create_form": create_form,
            "deposit_form": deposit_form,
            "withdraw_form": withdraw_form,

            "report_form": report_form,
            "statistics": statistics,
        },
    )