from django.shortcuts import render, get_object_or_404, redirect

from dashboard.utils import read_session_errors
from savings.models import SavingPlan, Transaction
from users.forms import InformationChangeForm, EmployeeChangeForm
from users.models import CustomUser

def employee_dashboard(request):
    return render(request, "employees/dashboard.html")

def manage_users(request):
    users = CustomUser.objects.all()
    return render(request, "employees/users.html", {"users": users})

def manage_saving_plans(request):
    saving_plans = SavingPlan.objects.all()
    return render(request, "employees/savings.html", {"saving_plans": saving_plans})

def manage_transactions(request):
    transactions = Transaction.objects.all()
    return render(request, "employees/transactions.html", {"transactions": transactions})

def manage_user_detail(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == "POST":
        match request.POST.get("form_type"):
            case "customer":
                customer_form = InformationChangeForm(request.POST, instance=request.user.customer)
                if customer_form.is_valid():
                    customer_form.save()
                    request.session["message_success"] = "Customer information updated successfully."
                else:
                    request.session["customer_form_errors"] = customer_form.errors
            case "employee":
                employee_form = EmployeeChangeForm(request.POST, instance=request.user)
                if employee_form.is_valid():
                    employee_form.save()
                    request.session["message_success"] = "Customer information updated successfully."
                else:
                    request.session["employee_form_error"] = employee_form.errors

        return redirect(request.path)

    else:
        if request.user.is_customer:
            customer_form = InformationChangeForm(instance=request.user)
            read_session_errors(customer_form, request.session, "customer_form_errors")
        else:
            customer_form = None

        employee_form = EmployeeChangeForm(request.user)
        read_session_errors(employee_form, request.session, "employee_form_errors")

    return render(request, "employees/user_detail.html", {
        "user": user,
        "customer_form": customer_form,
        "employee_form": employee_form,
        "message_success": request.session.pop("message_success", None)
    })

def manage_saving_plan_detail(request, account_number):
    pass

def manage_transaction_detail(request, transaction_id):
    pass