from datetime import date

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.forms import ModelChoiceField, HiddenInput 
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404

from budget import models, forms
from budget.widgets import *

def ensure_budget_profile(view, *args, **kwargs):
    @login_required(*args, **kwargs)
    def check(request, *args, **kwargs):
        try:
            request.user.budget_profile
        except models.UserProfile.DoesNotExist:
            request.user.budget_profile = models.UserProfile() 
            request.user.budget_profile.save()
            i = 0
            for cg in models.CategoryGroup.objects.filter(default=True).order_by('id'):
                ucg = models.UserCategoryGroup(category_group=cg, priority=cg.id)
                request.user.budget_profile.user_category_groups.add(ucg)
                for c in cg.categories.filter(default=True):
                    i += 1
                    uc = models.UserCategory(category=c, group=ucg, priority=i)
                    request.user.budget_profile.user_categories.add(uc)
            request.user.budget_profile.save()
        return view(request, *args, **kwargs)
    return check

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            return HttpResponseRedirect(reverse('index'))
    else:
        form = UserCreationForm()
    return render(request, "budget/register.html", {
        'form': form,
    })

@ensure_budget_profile
def budget(request, year=None, month=None):
    today = date.today()
    user = request.user.budget_profile
    if year == None:
        year = today.year
    else:
        year = int(year)
    if month == None:
        month = today.month
    else:
        month = int(month)
    today = date.today()
    first_month = date(year, month, 1)
    if month < 11:
        second_month = date(year, month % 12 + 1, 1)
        third_month = date(year, (month + 1) % 12 + 1, 1)
    elif month == 11:
        second_month = date(year, 12, 1)
        third_month = date(year+1, 1, 1)
    else:
        second_month = date(year+1, 1, 1)
        third_month = date(year+1, 2, 1)
    budget = user.budgets.filter(month__range=(first_month, third_month)).order_by('month')
    user_categories = user.user_categories.order_by('group__priority', 'category__group__name', 'priority')

    if request.method == "POST":
        formset = forms.BudgetFormSet(request.POST)
        if formset.is_valid():
            for form in formset:
                u = form.cleaned_data['user']
                del form.cleaned_data['user']
                b = form.cleaned_data['budget']
                del form.cleaned_data['budget']
                if u != user or b.user != user:
                    return HttpResponseForbidden("<h1>403 Forbidden</h1>")
                for category_name, amount in form.cleaned_data.items():
                    try:
                        bc = b.category_budget.get(budget__user=u, budget=b,
                                                   category__name=category_name)
                    except models.CategoryBudget.DoesNotExist:
                        c = get_object_or_404(models.Category, name=category_name)
                        bc = models.CategoryBudget(budget=b, category=c)
                    bc.amount = amount
                    bc.save()
    else:
        if budget.count() < 3:
            if not budget.filter(month=second_month).exists():
                models.Budget.objects.create(month=first_month, user=user)
            if not budget.filter(month=second_month).exists():
                models.Budget.objects.create(month=second_month, user=user)
            if not budget.filter(month=third_month).exists():
                models.Budget.objects.get_or_create(month=third_month, user=user)
            budget = user.budgets.filter(month__range=(first_month, third_month)).order_by('month')

        formset = forms.BudgetFormSet(initial=[{'user': user, 'budget': b} for b in budget])
    return render(request, 'budget/budget.html', 
            {'year': year, 'month': month, 'budget': budget, 'today': today,
             'user_categories': user_categories, 'formset': formset})

def get_transactions(user, account=None):
    if account:
        transfers = models.Transfer.objects.filter(to_account__user=user, 
                                                   to_account=account)
        transactions = list(account.transactions.all())
    else:
        transfers = models.Transfer.objects.filter(to_account__user=user)
        transactions = list(models.Transaction.objects.filter(account__user=user))
    transactions.extend(transfers.extra(
            select={'account_id': 'to_account_id', 'to_account_id': 'account_id',
                    'inflow': 'outflow', 'outflow': 'inflow'}))
    transactions.sort(key=lambda t: (t.date, t.added))
    return transactions

@ensure_budget_profile
def accounts(request):
    user = request.user.budget_profile
    transactions = get_transactions(user)
    return render(request, "budget/account.html",
                  {'transactions': transactions})

@ensure_budget_profile
def account(request, id):
    user = request.user.budget_profile
    account = get_object_or_404(models.Account, pk=id)
    transactions = get_transactions(user, account)
    if account.user.user != request.user:
        return HttpResponseForbidden("<h1>403 Forbidden</h1>")
    return render(request, "budget/account.html", {'account': account,
            'transactions': transactions})

@ensure_budget_profile
def delete_account(request, id):
    user = request.user.budget_profile
    account = get_object_or_404(models.Account, pk=id)

    if user != account.user:
        return HttpResponseForbidden("<h1>403 Forbidden</h1>")
    if request.method == "POST":
        account.delete()
        return HttpResponseRedirect(request.POST['next'])
    return render(request, "budget/delete_account.html", 
                  {'account': account, 'next': request.GET['next']})

@ensure_budget_profile
def add_account(request):
    user = request.user.budget_profile
    if request.method == "POST":
        if unicode(user.id) not in request.POST['user']:
            return HttpResponseForbidden("<h1>403 Forbidden</h1>")
        form = forms.AccountForm(request.POST)
        if form.is_valid():
            account = form.save()
            return HttpResponseRedirect(reverse('budget.views.account', kwargs={'id': account.id}))
    else:
        form = forms.AccountForm(initial={'user': user})
    return render(request, "budget/add_account.html", {'form': form}) 

def get_account(account_id=None):
    if account_id:
        account = get_object_or_404(models.Account, pk=account_id)
        return account
    return None

@ensure_budget_profile
def clear_transaction(request, id):
    user = request.user.budget_profile
    transaction = get_object_or_404(models.Transaction, pk=id)

    if user != transaction.account.user:
        return HttpResponseForbidden("<h1>403 Forbidden</h1>")
    transaction.cleared = not transaction.cleared
    transaction.save()
    return HttpResponseRedirect(request.GET.get('next', reverse(accounts)))

@ensure_budget_profile
def delete_transaction(request, id):
    user = request.user.budget_profile
    transaction = get_object_or_404(models.Transaction, pk=id)

    if user != transaction.account.user:
        return HttpResponseForbidden("<h1>403 Forbidden</h1>")
    if request.method == "POST":
        transaction.delete()
        return HttpResponseRedirect(request.POST['next'])
    return render(request, "budget/delete_transaction.html", 
                  {'transaction': transaction, 'next': request.GET['next']})

@ensure_budget_profile
def add_transaction(request, account_id=None):
    user = request.user.budget_profile
    account = get_account(account_id)

    if account and account.user.user != request.user:
        return HttpResponseForbidden("<h1>403 Forbidden</h1>")

    transactions = get_transactions(user, account)
    if account:
        Form = forms.TransactionToAccountForm
    else:
        Form = forms.TransactionForm

    Form.base_fields['category'] = ModelChoiceField(
            queryset=models.Category.objects.filter(Q(users__user=user)|Q(default=True)),
            empty_label="None")

    if request.method == "POST":
        if account and unicode(account.id) not in request.POST['account']:
            return HttpResponseForbidden("<h1>403 Forbidden</h1>")
        form = Form(request.POST)
        if form.is_valid():
            transaction = form.save()
            if account:
                return HttpResponseRedirect(reverse('budget.views.account', kwargs={'id': account_id}))
            else:
                return HttpResponseRedirect(reverse('budget.views.accounts'))
    else:
        form = Form(initial={'account': account, 'date': date.today()})
    return render(request, "budget/add_transaction.html", 
            {'form': form, 'account': account, 'transactions': transactions}) 
     
@ensure_budget_profile
def add_transfer(request, account_id=None):
    user = request.user.budget_profile
    account = get_account(account_id)

    if account and account.user.user != request.user:
        return HttpResponseForbidden("<h1>403 Forbidden</h1>")

    transactions = get_transactions(user, account)
    if account:
        Form = forms.TransferToAccountForm
    else:
        Form = forms.TransferForm

    Form.base_fields['to_account'] = ModelChoiceField(
            queryset=models.Account.objects.filter(user=user).exclude(pk=account_id))
    Form.base_fields['category'] = ModelChoiceField(
            queryset=models.Category.objects.filter(Q(users__user=user)|Q(default=True)),
            empty_label="None")

    if request.method == "POST":
        if account and unicode(account.id) not in request.POST['account']:
            return HttpResponseForbidden("<h1>403 Forbidden</h1>")
        form = Form(request.POST)
        if form.is_valid():
            transaction = form.save()
            if account:
                return HttpResponseRedirect(reverse('budget.views.account', kwargs={'id': account_id}))
            else:
                return HttpResponseRedirect(reverse('budget.views.accounts'))
    else:
        form = Form(initial={'account': account, 'date': date.today()})
    return render(request, "budget/add_transfer.html", 
            {'form': form, 'account': account, 'transactions': transactions}) 
