from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash, login
from .forms import EmailChangeForm

@login_required
def profile(request):
    if request.method == "POST":
        if request.POST.get("form_type") == "password":
            password_form = PasswordChangeForm(request.user, request.POST)
            email_form = EmailChangeForm(user=request.user)

            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)

        elif request.POST.get("form_type") == "email":
            email_form = EmailChangeForm(request.POST, user=request.user)
            password_form = PasswordChangeForm(request.user)

            if email_form.is_valid():
                email_form.save()

    else:
        password_form = PasswordChangeForm(request.user)
        email_form = EmailChangeForm(user=request.user)

    return render(request, "account/profile.html", {
        "password_form": password_form,
        "email_form": email_form,
    })