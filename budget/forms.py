from django.forms import ModelForm, HiddenInput 

from budget.models import Account, Transaction, Transfer

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

