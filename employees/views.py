from django.shortcuts import render, get_object_or_404, redirect

from dashboard.utils import read_session_errors
from savings.models import SavingPlan, Transaction
from users.forms import InformationChangeForm
from users.models import CustomUser
from .forms import EmployeeChangeForm, UserCreateForm


def employee_dashboard(request):
    return render(request, "employees/dashboard.html")

def manage_users(request):
    users = CustomUser.objects.all()
    return render(request, "employees/users/users.html", {
        "users": users,
        "message_success": request.session.pop("message_success", None)
    })

def manage_saving_plans(request):
    saving_plans = SavingPlan.objects.all()
    return render(request, "employees/savings/savings.html", {"saving_plans": saving_plans})

def manage_transactions(request):
    transactions = Transaction.objects.all()
    return render(request, "employees/savings/transactions.html", {"transactions": transactions})

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