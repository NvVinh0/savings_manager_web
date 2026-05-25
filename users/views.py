from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render

from dashboard.decorators import customer_required
from dashboard.utils import read_session_errors
from users.forms import EmailChangeForm, InformationChangeForm

@customer_required
def profile(request):
    if request.method == "POST":
        match request.POST.get("form_type"):
            case "information":
                information_form = InformationChangeForm(request.POST, instance=request.user.customer)
                if information_form.is_valid():
                    information_form.save()
                    request.session["message_success"] = "Information updated successfully."
                else:
                    request.session["info_form_errors"] = information_form.errors
            case "password":
                password_form = PasswordChangeForm(request.user, request.POST)

                if password_form.is_valid():
                    user = password_form.save()
                    request.session["message_success"] = "Password updated successfully."
                    update_session_auth_hash(request, user)
                else:
                    request.session["password_form_errors"] = password_form.errors
            case "email":
                email_form = EmailChangeForm(request.POST, user=request.user)

                if email_form.is_valid():
                    email_form.save()
                    request.session["message_success"] = "Email updated successfully."
                else:
                    request.session["email_form_errors"] = email_form.errors

        return redirect("profile")

    else:
        information_form = InformationChangeForm(instance=request.user.customer)
        password_form = PasswordChangeForm(request.user)
        email_form = EmailChangeForm(user=request.user)
        read_session_errors(information_form, request.session, "info_form_errors")
        read_session_errors(password_form, request.session, "password_form_errors")
        read_session_errors(email_form, request.session, "email_form_errors")

    return render(request, "account/profile.html", {
        "information_form": information_form,
        "password_form": password_form,
        "email_form": email_form,
        "message_success": request.session.pop("message_success", None)
    })