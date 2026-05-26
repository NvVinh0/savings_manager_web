from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction as db_transaction
from django.db.models import Q, Sum, Count
from django.utils.dateparse import parse_date
from django.utils.timezone import now
from decimal import Decimal
from django.contrib import messages
from dashboard.utils import read_session_errors
from savings.models import SavingPlan, Transaction, TransactionType
from savings.services import get_statistics
from users.forms import InformationChangeForm
from users.models import CustomUser, Customer
from .forms import EmployeeChangeForm, UserCreateForm, SavingTypeEditForm, SavingPlanEditForm
from savings.models import SavingPlan, SavingType, Transaction, TransactionType
from savings.services import create_account
from django import forms

def employee_dashboard(request):
    today = now().date()
    month_start = today.replace(day=1)
    month_label = today.strftime("%Y-%m")

    daily_statistics = get_statistics("day", date=today)
    monthly_statistics = get_statistics("month", month=month_label)
    opened_this_month = SavingPlan.objects.filter(created_at__date__gte=month_start).count()
    closed_this_month = monthly_statistics["closed_count"]

    return render(request, "employees/dashboard.html", {
        "deposit_report": {
            "deposits": daily_statistics["total_deposit"],
            "withdrawals": daily_statistics["total_withdraw"],
            "difference": daily_statistics["total_deposit"] - daily_statistics["total_withdraw"],
        },
        "saving_plan_report": {
            "opened": opened_this_month,
            "closed": closed_this_month,
            "difference": opened_this_month - closed_this_month,
        },
    })

def manage_users(request):
    users = CustomUser.objects.select_related("customer", "employee").all()

    query = request.GET.get("search", "").strip()
    user_type = request.GET.get("type", "")

    if query:
        users = users.filter(
            Q(email__icontains=query) or
            Q(customer__full_name__icontains=query) or
            Q(customer__citizen_id__icontains=query) or
            Q(employee__role__icontains=query)
        )

    if user_type == "customer":
        users = users.filter(customer__isnull=False)
    elif user_type == "employee":
        users = users.filter(employee__isnull=False)

    return render(request, "employees/users/users.html", {
        "users": users,
        "message_success": request.session.pop("message_success", None)
    })

def manage_saving_plans(request):
    saving_plans = SavingPlan.objects.all()
    return render(request, "employees/savings/savings.html", {"saving_plans": saving_plans})

def manage_transactions(request):
    transactions = Transaction.objects.select_related("saving_plan").order_by("-timestamp")

    query = request.GET.get("search")
    transaction_type = request.GET.get("type")

    if query:
        transactions = transactions.filter(saving_plan__id__icontains=query)

    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)

    return render(request, "employees/savings/transactions.html", {
        "transactions": transactions,
        "transaction_types": TransactionType.choices,
    })

def manage_user_detail(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == "POST":
        match request.POST.get("form_type"):
            case "customer":
                customer_form = InformationChangeForm(request.POST, instance=user.customer)
                if customer_form.is_valid():
                    customer_form.save()
                    request.session["message_success"] = "Customer information updated successfully."
                else:
                    request.session["customer_form_errors"] = customer_form.errors
            case "employee":
                action = request.POST.get("action")
                if action == "remove":
                    if user.is_employee:
                        if not user.is_customer:
                            # if user is not a customer, delete the user
                            user.delete()
                            request.session["message_success"] = "User deleted successfully."
                            return redirect(manage_users)
                        else:
                            user.employee.delete()
                            request.session["message_success"] = "Employee access updated successfully."
                    else:
                        request.session["employee_form_errors"] = { "__all__": ["User is not Employee"] }
                else:
                    employee_form = EmployeeChangeForm(request.POST, user=user)
                    if employee_form.is_valid():
                        employee_form.save()
                        request.session["message_success"] = "Employee access updated successfully."
                    else:
                        request.session["employee_form_errors"] = employee_form.errors

        return redirect(request.path)
    else:
        if user.is_customer:
            customer_form = InformationChangeForm(instance=user.customer)
            read_session_errors(customer_form, request.session, "customer_form_errors")
        else:
            customer_form = None

        employee_form = EmployeeChangeForm(user=user)
        read_session_errors(employee_form, request.session, "employee_form_errors")

    return render(request, "employees/users/user_detail.html", {
        "user": user,
        "customer_form": customer_form,
        "employee_form": employee_form,
        "message_success": request.session.pop("message_success", None)
    })

def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            request.session["message_success"] = "Successfully created user."
        else:
            request.session["form_errors"] = form.errors

        return redirect(manage_users)
    else:
        form = UserCreateForm()
        read_session_errors(form, request.session, "form_errors")

    return render(request, "employees/users/user_create.html", { "form": form })

def manage_saving_plan_detail(request, account_number):
    pass

def manage_reports(request):
    today = now().date()
    current_month = today.strftime("%Y-%m")
    selected_report = request.GET.get("report", "cash")

    if selected_report not in {"cash", "plans"}:
        selected_report = "cash"

    selected_date = parse_date(request.GET.get("date", "")) or today
    if selected_date > today:
        selected_date = today

    selected_month = request.GET.get("month") or current_month
    try:
        selected_year_value, selected_month_value = selected_month.split("-")
        selected_year_value = int(selected_year_value)
        selected_month_value = int(selected_month_value)
        selected_month_date = parse_date(f"{selected_month}-01")
        current_month_date = today.replace(day=1)
        if selected_month_date is None or selected_month_value < 1 or selected_month_value > 12:
            raise ValueError
        if selected_month_date > current_month_date:
            selected_month = current_month
            selected_year_value = today.year
            selected_month_value = today.month
    except ValueError:
        selected_month = current_month
        selected_year_value = today.year
        selected_month_value = today.month

    report = None
    if selected_report == "cash":
        statistics = get_statistics("day", date=selected_date)
        report = {
            "type": "cash",
            "label": selected_date,
            "deposits": statistics["total_deposit"],
            "withdrawals": statistics["total_withdraw"],
            "difference": statistics["total_deposit"] - statistics["total_withdraw"],
        }
    else:
        statistics = get_statistics("month", month=selected_month)
        opened_count = SavingPlan.objects.filter(
            created_at__year=selected_year_value,
            created_at__month=selected_month_value,
        ).count()
        closed_count = statistics["closed_count"]
        report = {
            "type": "plans",
            "label": selected_month,
            "opened": opened_count,
            "closed": closed_count,
            "difference": opened_count - closed_count,
        }

    return render(request, "employees/savings/reports.html", {
        "report": report,
        "selected_report": selected_report,
        "selected_date": selected_date,
        "selected_month": selected_month,
        "today": today,
        "current_month": current_month,
    })
def _employee_saving_create_form(data=None):
    """Form khớp template savings.html (name, citizen_id, address, balance, saving_type)."""
    form_class = type(
        "EmployeeSavingCreateForm",
        (forms.Form,),
        {
            "name": forms.CharField(max_length=50, required=True),
            "citizen_id": forms.CharField(max_length=12, min_length=12, required=True),
            "address": forms.CharField(max_length=100, required=False),
            "balance": forms.DecimalField(
                max_digits=12,
                decimal_places=2,
                min_value=Decimal("0"),
                required=True,
            ),
            "saving_type": forms.ModelChoiceField(
                queryset=SavingType.objects.filter(is_active=True).order_by("name"),
                required=True,
            ),
        },
    )
    return form_class(data)


def _get_or_create_customer(name, citizen_id, address):
    customer = Customer.objects.filter(citizen_id=citizen_id).select_related("user").first()
    if customer:
        return customer

    email = f"{citizen_id}@customer.com"
    user = CustomUser.objects.filter(email=email).first()
    if user is None:
        user = CustomUser.objects.create_user(email=email, password=citizen_id)

    return Customer.objects.create(
        user=user,
        full_name=name,
        citizen_id=citizen_id,
        address=address or "",
    )


def _parse_post_amount(raw_amount):
    try:
        amount = Decimal(str(raw_amount).strip())
    except Exception:
        return None
    if amount <= 0:
        return None
    return amount


def _employee_deposit(plan, amount):
    """Gửi tiền từ màn employee — không áp rule đáo hạn/min của khách."""
    with db_transaction.atomic():
        plan.refresh_from_db()
        balance_before = plan.balance
        plan.balance = balance_before + amount
        plan.save(update_fields=["balance"])
        Transaction.objects.create(
            transaction_type=TransactionType.DEPOSIT,
            balance_before=balance_before,
            amount=amount,
            balance_after=plan.balance,
            saving_plan=plan,
        )


def _employee_withdraw(plan, amount):
    """Rút tiền từ màn employee — rút một phần, không đóng TK."""
    with db_transaction.atomic():
        plan.refresh_from_db()
        if amount > plan.balance:
            raise ValueError("Insufficient balance")
        balance_before = plan.balance
        plan.balance = balance_before - amount
        plan.save(update_fields=["balance"])
        Transaction.objects.create(
            transaction_type=TransactionType.WITHDRAW,
            balance_before=balance_before,
            amount=amount,
            balance_after=plan.balance,
            saving_plan=plan,
        )


def _redirect_savings_list(request):
    """Giữ bộ lọc GET sau POST."""
    url = redirect("manage_saving_accounts").url
    query = request.GET.urlencode()
    if query:
        return redirect(f"{url}?{query}")
    return redirect("manage_saving_accounts")


def manage_saving_plans(request):
    plans = (SavingPlan.objects.select_related("saving_type", "customer", "customer__user").filter(is_active=True).order_by("-created_at"))
    search = request.GET.get("search", "").strip()
    filter_by = request.GET.get("filter_by", "account_number")

    if search:
        filter_map = {
            "account_number": Q(account_number__icontains=search),
            "name": Q(customer__full_name__icontains=search),
            "citizen_id": Q(customer__citizen_id__icontains=search),
            "address": Q(customer__address__icontains=search),
            "saving_type": Q(saving_type__name__icontains=search),
        }
        plans = plans.filter(filter_map.get(filter_by, filter_map["account_number"]))

    stats = SavingPlan.objects.aggregate(total_accounts=Count("account_number"),total_balance=Sum("balance"),)
    active_count = SavingPlan.objects.filter(is_active=True).count()

    create_form = _employee_saving_create_form()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create":
            create_form = _employee_saving_create_form(request.POST)
            if create_form.is_valid():
                cd = create_form.cleaned_data
                try:
                    customer = _get_or_create_customer(
                        cd["name"],
                        cd["citizen_id"],
                        cd.get("address", ""),
                    )
                    create_account(
                        initial_balance=cd["balance"],
                        user=customer.user,
                        saving_type=cd["saving_type"],
                    )
                    messages.success(request, "Account created successfully.")
                except ValueError as exc:
                    messages.error(request, str(exc))
            else:
                messages.error(request, "Please check the create account form.")
            return _redirect_savings_list(request)

        if action in ("deposit", "withdraw"):
            account_number = request.POST.get("account_number", "").strip()
            amount = _parse_post_amount(request.POST.get("amount"))

            if not account_number:
                messages.error(request, "Account number is required.")
                return _redirect_savings_list(request)

            if amount is None:
                messages.error(request, "Invalid amount.")
                return _redirect_savings_list(request)

            plan = SavingPlan.objects.filter(
                account_number=account_number,
                is_active=True,
            ).select_related("saving_type").first()
            if plan is None:
                messages.error(request, "Saving account not found or inactive.")
                return _redirect_savings_list(request)

            try:
                if action == "deposit":
                    _employee_deposit(plan, amount)
                    messages.success(
                        request,
                        f"Deposited {amount:,.2f} to {account_number}. New balance: {plan.balance:,.2f}",
                    )
                else:
                    _employee_withdraw(plan, amount)
                    plan.refresh_from_db()
                    messages.success(
                        request,
                        f"Withdrew {amount:,.2f} from {account_number}. New balance: {plan.balance:,.2f}",
                    )
            except ValueError as exc:
                messages.error(request, str(exc))
            return _redirect_savings_list(request)

        messages.error(request, "Unknown action.")
        return _redirect_savings_list(request)

    return render(
        request,
        "employees/savings/savings.html",
        {
            "saving_plans": plans,
            "create_form": create_form,
            "stats": {
                "total_accounts": stats["total_accounts"] or 0,
                "total_balance": stats["total_balance"] or 0,
                "active_count": active_count,
            },
        },
    )

def manage_saving_plan_detail(request, account_number):
    saving_plan = get_object_or_404(
        SavingPlan.objects.select_related("saving_type", "customer"),
        account_number=account_number,
    )

    transactions = (
        saving_plan.transactions
        .select_related("saving_plan")
        .order_by("-timestamp")
    )

    return render(
        request,
        "employees/savings/saving_detail.html",
        {
            "saving_plan": saving_plan,
            "transactions": transactions,
        },
    )

def edit_saving_type(request, saving_type_id):
    saving_type = get_object_or_404(SavingType, pk=saving_type_id)

    if request.method == "POST":
        form = SavingTypeEditForm(request.POST, instance=saving_type)
        if form.is_valid():
            form.save()
            messages.success(request, "Saving type updated successfully.")
            return redirect("manage_saving_accounts")
        else:
            messages.error(request, "Please check the form for errors.")
    else:
        form = SavingTypeEditForm(instance=saving_type)

    return render(
        request,
        "employees/savings/edit_saving_type.html",
        {
            "form": form,
            "saving_type": saving_type,
        },
    )

def edit_saving_plan(request, account_number):
    saving_plan = get_object_or_404(
        SavingPlan.objects.select_related("saving_type", "customer"),
        account_number=account_number,
    )

    if request.method == "POST":
        form = SavingPlanEditForm(request.POST, instance=saving_plan)
        if form.is_valid():
            form.save()
            messages.success(request, "Saving plan updated successfully.")
            return redirect("manage_saving_plan_detail", account_number=account_number)
        else:
            messages.error(request, "Please check the form for errors.")
    else:
        form = SavingPlanEditForm(instance=saving_plan)

    return render(
        request,
        "employees/savings/edit_saving_plan.html",
        {
            "form": form,
            "saving_plan": saving_plan,
        },
    )