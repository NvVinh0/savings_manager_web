from django.shortcuts import render

def saving_accounts(request):
    return render(request, "savings/saving_accounts.html")