from decimal import Decimal

from django import forms

from savings.models import SavingAccount, SavingType


class CreateSavingAccountForm(forms.Form):
    name = forms.CharField(max_length=50)
    citizen_id = forms.CharField(max_length=12)
    address = forms.CharField(max_length=100)
    balance = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    saving_type = forms.ModelChoiceField(queryset=SavingType.objects.filter(is_active=True))


class DepositForm(forms.Form):
    account = forms.ModelChoiceField(queryset=SavingAccount.objects.none(), empty_label="Select account")
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))

    def __init__(self, *args, accounts_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if accounts_qs is not None:
            self.fields["account"].queryset = accounts_qs


class WithdrawForm(forms.Form):
    account = forms.ModelChoiceField(queryset=SavingAccount.objects.none(), empty_label="Select account")
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        help_text="For fixed-term accounts, amount is ignored and full balance is withdrawn.",
    )

    def __init__(self, *args, accounts_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if accounts_qs is not None:
            self.fields["account"].queryset = accounts_qs
