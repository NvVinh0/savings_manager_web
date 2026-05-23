from allauth.account.forms import SignupForm
from django import forms
from .models import Customer, EmployeeRole, Employee


class CustomSignupForm(SignupForm):
    full_name = forms.CharField(max_length=50)
    citizen_id = forms.CharField(max_length=12)
    address = forms.CharField(max_length=100)

    def save(self, request):
        user = super().save(request)

        Customer.objects.create(
            user=user,
            full_name=self.cleaned_data["full_name"],
            citizen_id=self.cleaned_data["citizen_id"],
            address=self.cleaned_data["address"],
        )

        return user

class InformationChangeForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "full_name",
            "citizen_id",
            "address",
        ]

class EmailChangeForm(forms.Form):
    email = forms.EmailField(label="New email")
    confirm_email = forms.EmailField(label="Confirm email")
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data:
            return cleaned_data

        email = cleaned_data.get("email")
        confirm_email = cleaned_data.get("confirm_email")

        if email and confirm_email and email != confirm_email:
            self.add_error("confirm_email", "Emails do not match")

        return cleaned_data

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not self.user.check_password(password):
            raise forms.ValidationError("Incorrect password")
        return password

    def save(self):
        self.user.email = self.cleaned_data["email"]
        self.user.save()

class EmployeeChangeForm(forms.Form):
    hasRead = forms.BooleanField(required=False)
    hasWrite = forms.BooleanField(required=False)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if self.user.is_employee:
            self.fields["hasRead"].initial = True
            self.fields["hasWrite"].initial = (
                    user.employee.role == EmployeeRole.WRITE
            )

            # Can't remove read while write exists
            if user.employee.role == EmployeeRole.WRITE:
                self.fields["hasRead"].disabled = True

    def clean(self):
        cleaned_data = super().clean()

        has_write = cleaned_data.get("hasWrite")
        if has_write:
            cleaned_data["hasRead"] = True

        return cleaned_data

    def save(self):
        has_read = self.cleaned_data["hasRead"]
        has_write = self.cleaned_data["hasWrite"]

        if not has_read:
            if self.user.is_employee:
                self.user.employee.delete()
            return None

        if has_write:
            role = EmployeeRole.WRITE
        else:
            role = EmployeeRole.READ

        employee, created = Employee.objects.get_or_create(user=self.user, defaults={"role": role})
        if not created: # exist, update role
            employee.role = role
            employee.save()

        return employee