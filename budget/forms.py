from django.forms import *
from django.forms.formsets import formset_factory

from budget.models import *

class AccountForm(ModelForm):
    class Meta:
        model = Account
        widgets = {
                'user': HiddenInput()
            }

class TransactionForm(ModelForm):
    class Meta:
        model = Transaction
        exclude = ['added']

class TransactionToAccountForm(TransactionForm):
    class Meta:
        model = Transaction
        exclude = ['added']
        widgets = {
                'account': HiddenInput()
            }

class TransferForm(TransactionForm):
    class Meta:
        model = Transfer
        exclude = ['added', 'payee']

class TransferToAccountForm(TransferForm):
    class Meta:
        model = Transaction
        exclude = ['added']
        widgets = {
                'account': HiddenInput()
            }

class BudgetForm(Form):
    def __init__(self, *args, **kwargs):
        try:
            if len(args) > 4: 
                user = args[4]['user']
            else:
                user = kwargs['initial']['user']
            if not isinstance(user, UserProfile):
                raise KeyError()
        except KeyError:
            if len(args) > 3:
                prefix = args[3]
            else:
                prefix = kwargs.get('prefix', '')
            if len(prefix) > 0:
                prefix += "-"
            try:
                if len(args) > 0:
                    user_id = args[0][prefix+'user'][0]
                else:
                    user_id = kwargs['data'][prefix+'user'][0]
                user = UserProfile.objects.get(id=user_id) 
            except (IndexError, KeyError, UserProfile.DoesNotExist):
                raise ValueError("Expect 'user' in initial or data")
        try:
            if len(args) > 4: 
                budget = args[4]
            else:
                budget = kwargs['initial']['budget']
            if not isinstance(budget, Budget):
                raise KeyError()
        except KeyError:
            if len(args) > 3:
                prefix = args[3]
            else:
                prefix = kwargs.get('prefix', '')
            if len(prefix) > 0:
                prefix += "-"
            try:
                if len(args) > 0:
                    budget_id = args[0][prefix+'budget'][0]
                else:
                    budget_id = kwargs['data'][prefix+'budget'][0]
                budget = Budget.objects.get(id=budget_id) 
            except (IndexError, KeyError, UserProfile.DoesNotExist):
                raise ValueError("Expect 'budget' in initial or data")
        super(BudgetForm, self).__init__(*args, **kwargs)

        self.fields['user'] = ModelChoiceField(queryset=UserProfile.objects.all(),widget=HiddenInput(),
                                             initial=user)
        self.fields['budget'] = ModelChoiceField(queryset=user.budgets.all(), widget=HiddenInput(), initial=budget)
        for user_category in user.user_categories.order_by('group__priority', 'category__group__name', 'priority'):
            try:
                category_budget_amount = CategoryBudget.objects.get_or_create(
                        budget=budget, category=user_category.category)[0].amount
            except CategoryBudget.DoesNotExist:
                category_budget_amount = 0
            self.fields[user_category.category.name] = DecimalField(
                    max_digits=20, decimal_places=2, required=False, 
                    label=user_category.category.name, widget=TextInput(),
                    initial="{:0.2f}".format(category_budget_amount))

BudgetFormSet = formset_factory(BudgetForm, extra=2, max_num=3)
