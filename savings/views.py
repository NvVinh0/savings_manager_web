from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def saving_accounts(request):
    return render(request, "savings/saving_accounts.html")