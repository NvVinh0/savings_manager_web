from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction

from dashboard.decorators import employee_required, employee_write_required
from dashboard.utils import read_session_errors
from savings.models import TransactionType
from users.forms import InformationChangeForm
from .forms import EmployeeChangeForm, UserCreateForm, SavingTypeEditForm
from .services import (
    build_report_context,
    get_dashboard_reports,
    get_saving_plan_by_id,
    get_saving_plan_transactions,
    get_saving_type_by_id,
    get_user_by_id,
    remove_employee_access,
    search_saving_plans,
    search_transactions,
    search_users,
)

@employee_required
def employee_dashboard(request):
    return render(request, "employees/dashboard.html", get_dashboard_reports())

@employee_required
def manage_users(request):
    users = search_users(
        query=request.GET.get("search", ""),
        user_type=request.GET.get("type", ""),
    )

    return render(request, "employees/users/users.html", {
        "users": users,
        "message_success": request.session.pop("message_success", None)
    })

@employee_required
def manage_transactions(request):
    transactions = search_transactions(
        query=request.GET.get("search", ""),
        transaction_type=request.GET.get("type", ""),
    )

    return render(request, "employees/savings/transactions.html", {
        "transactions": transactions,
        "transaction_types": TransactionType.choices,
    })

@employee_required
def manage_user_detail(request, user_id):
    selected_user = get_user_by_id(user_id)

    if request.method == "POST":
        match request.POST.get("form_type"):
            case "customer":
                customer_form = InformationChangeForm(request.POST, instance=selected_user.customer)
                if customer_form.is_valid():
                    customer_form.save()
                    request.session["message_success"] = "Customer information updated successfully."
                else:
                    request.session["customer_form_errors"] = customer_form.errors
            case "employee":
                action = request.POST.get("action")
                if action == "remove":
                    try:
                        result = remove_employee_access(selected_user)
                        if result == "deleted":
                            request.session["message_success"] = "User deleted successfully."
                            return redirect("manage_users")
                        request.session["message_success"] = "Employee access updated successfully."
                    except ValueError as exc:
                        request.session["employee_form_errors"] = { "__all__": [str(exc)] }
                else:
                    employee_form = EmployeeChangeForm(request.POST, user=selected_user)
                    if employee_form.is_valid():
                        employee_form.save()
                        request.session["message_success"] = "Employee access updated successfully."
                    else:
                        request.session["employee_form_errors"] = employee_form.errors

        return redirect(request.path)
    else:
        if selected_user.is_customer:
            customer_form = InformationChangeForm(instance=selected_user.customer)
            read_session_errors(customer_form, request.session, "customer_form_errors")
        else:
            customer_form = None

        employee_form = EmployeeChangeForm(user=selected_user)
        read_session_errors(employee_form, request.session, "employee_form_errors")

    return render(request, "employees/users/user_detail.html", {
        "selected_user": selected_user,
        "customer_form": customer_form,
        "employee_form": employee_form,
        "message_success": request.session.pop("message_success", None)
    })

@employee_write_required
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

@employee_required
def manage_reports(request):
    selected_report = request.GET.get("report", "cash")

    context = build_report_context(
        selected_report,
        request.GET.get("date", ""),
        request.GET.get("month", ""),
    )
    return render(request, "employees/savings/reports.html", context)

@employee_required
def manage_saving_plans(request):
    search = request.GET.get("search", "").strip()
    saving_plans = search_saving_plans(search)

    return render(
        request,
        "employees/savings/savings.html",
        {
            "saving_plans": saving_plans,
            "search": search,
        },
    )

@employee_required
def manage_saving_plan_detail(request, plan_id):
    saving_plan = get_saving_plan_by_id(plan_id)
    transactions = get_saving_plan_transactions(saving_plan)

    return render(
        request,
        "employees/savings/saving_detail.html",
        {
            "saving_plan": saving_plan,
            "transactions": transactions,
        },
    )

@employee_required
def manage_saving_types(request):
    pass

@employee_required
def manage_saving_type_detail(request, saving_type_id):
    saving_type = get_saving_type_by_id(saving_type_id)

    if request.method == "POST":
        form = SavingTypeEditForm(request.POST, instance=saving_type)
        if form.is_valid():
            duration_changed = form.cleaned_data["duration_months"] != saving_type.duration_months

            if duration_changed:
                with transaction.atomic():
                    # Keep old product definition for audit/history.
                    saving_type.is_active = False
                    saving_type.save(update_fields=["is_active"])

                    new_saving_type = form.save(commit=False)
                    new_saving_type.pk = None
                    new_saving_type.save()

                messages.success(request, "Duration changed. Created a new saving type and deactivated the old one.")
                return redirect("manage_saving_type_detail", saving_type_id=new_saving_type.id)

            form.save()
            messages.success(request, "Saving type updated successfully.")
            return redirect("manage_saving_type_detail", saving_type_id=saving_type.id)
        messages.error(request, "Please check the form for errors.")
    else:
        form = SavingTypeEditForm(instance=saving_type)

    return render(
        request,
        "employees/savings/saving_types.html",
        {
            "form": form,
            "saving_type": saving_type,
        },
    )

