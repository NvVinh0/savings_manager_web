from django import forms

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