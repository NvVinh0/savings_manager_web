from django.contrib import messages
from django.shortcuts import redirect, render
from django.db.models import Q

from dashboard.decorators import customer_required
from savings.forms import (
    CreateSavingPlanForm,
    SavingPlanActionForm,
)

from savings.services import (
    create_saving_plan,
    deposit,
    get_active_saving_types,
    get_plans_by_user,
    withdraw,
)

@customer_required
def saving_plans(request):
    saving_plans = get_plans_by_user(request.user)
    search = request.GET.get("search", "").strip()
    if search:
        saving_plans = saving_plans.filter(
            Q(plan_id__icontains=search) | Q(saving_type__name__icontains=search)
        )
    create_form = CreateSavingPlanForm(prefix="create")

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        try:
            if form_type == "create":
                create_form = CreateSavingPlanForm(request.POST, prefix="create")

                if create_form.is_valid():
                    create_saving_plan(
                        customer=request.user.customer,
                        saving_type=create_form.cleaned_data["saving_type"],
                        initial_balance=create_form.cleaned_data["initial_balance"],
                    )
                    messages.success(request, "Saving plan created successfully.")
                    return redirect("saving_plans")

        except ValueError as exc:
            messages.error(request, str(exc))

    return render(
        request,
        "savings/saving_plans.html",
        {
            "saving_plans": saving_plans,
            "search": search,
            "create_form": create_form,
        },
    )

@customer_required
def saving_types(request):
    return render(
        request,
        "savings/saving_types.html",
        {"saving_types": get_active_saving_types()},
    )

@customer_required
def saving_plan_detail(request, plan_id):
    saving_plan = get_plans_by_user(request.user).filter(plan_id=plan_id).first()
    if saving_plan is None:
        messages.error(request, "Saving plan not found.")
        return redirect("saving_plans")

    action_form = SavingPlanActionForm(prefix="action")
    if request.method == "POST":
        action_form = SavingPlanActionForm(request.POST, prefix="action")
        if action_form.is_valid():
            action = action_form.cleaned_data["action"]
            amount = action_form.cleaned_data["amount"]
            if action == "deposit":
                deposit(saving_plan, amount)
                messages.success(request, "Deposit completed.")
            else:
                withdraw(saving_plan, amount)
                messages.success(request, "Withdrawal completed.")
            return redirect("saving_plan_detail", plan_id=plan_id)

    transactions = saving_plan.transactions.order_by("-timestamp")
    return render(request, "savings/saving_plan_detail.html", {
        "saving_plan": saving_plan,
        "transactions": transactions,
        "action_form": action_form,
    })
