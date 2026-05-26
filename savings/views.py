from django.contrib import messages
from django.shortcuts import redirect, render

from dashboard.decorators import customer_required
from savings.forms import (
    TransactionForm,
    ReportForm,
)

from savings.models import SavingType, Transaction

from savings.services import (
    create_saving_plan,
    deposit,
    get_plans_by_user,
    withdraw,
    get_statistics,
)

@customer_required
def saving_accounts(request):
    accounts = get_plans_by_user(request.user)
    saving_types = SavingType.objects.filter(is_active=True).order_by("name")
    transaction_form = TransactionForm(prefix="txn", accounts_qs=accounts)

    report_form = ReportForm(accounts_qs=accounts)
    statistics = None

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        try:
            if form_type == "transaction":
                transaction_form = TransactionForm(request.POST, prefix="txn", accounts_qs=accounts)

                if transaction_form.is_valid():
                    action = transaction_form.cleaned_data["action"]

                    if action == "create":
                        create_saving_plan(user=request.user, saving_type=transaction_form.cleaned_data["saving_type"],
                                           initial_balance=transaction_form.cleaned_data["initial_balance"])
                        messages.success(request, "Saving account created successfully.")
                    elif action == "deposit":
                        account = transaction_form.cleaned_data["account"]
                        amount = transaction_form.cleaned_data["amount"]
                        deposit(account, amount)
                        messages.success(request, "Deposit completed.")
                    else:
                        account = transaction_form.cleaned_data["account"]
                        amount = transaction_form.cleaned_data["amount"]
                        withdraw(account, amount)
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
                        period=period_type,
                        saving_plan=account,
                        date=date,
                        month=month,
                        year=year,
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
            "transaction_form": transaction_form,

            "report_form": report_form,
            "statistics": statistics,
        },
    )

@customer_required
def transactions(request):
    accounts = request.user.customer.saving_accounts.select_related("saving_type").order_by("plan_id")
    selected_account_number = request.GET.get("account", "")
    selected_account = None
    transactions = Transaction.objects.none()

    if selected_account_number:
        selected_account = accounts.filter(account_number=selected_account_number).first()
        if selected_account:
            transactions = selected_account.transactions.order_by("-timestamp")

    return render(request, "savings/transactions.html", {
        "accounts": accounts,
        "selected_account": selected_account,
        "selected_account_number": selected_account_number,
        "transactions": transactions,
    })
