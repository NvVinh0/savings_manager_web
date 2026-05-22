from django.shortcuts import render, get_object_or_404

from users.models import CustomUser


def employee_dashboard(request):
    return render(request, "employees/dashboard.html")

def manage_users(request):
    users = CustomUser.objects.all()
    return render(request, "employees/users.html", {"users": users})

def manage_user_profile(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    return render(request, "employees/user_profile.html", {"user": user})

def manage_saving_accounts(request):
    pass

def manage_transactions(request):
    pass