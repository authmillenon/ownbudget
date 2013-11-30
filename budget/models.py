"""
Django models
"""
import datetime

from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core import validators
from django.core.exceptions import ValidationError
from django.utils.translation import get_language_info

def money_field(*args, **kwargs):
    return models.DecimalField(max_digits=20, decimal_places=2, blank=False,
                               default=0, *args, **kwargs)

def today_is_the_day(weekday):
    return lambda: datetime.date().isoweekday() == weekday

def is_first_of_month(value):
    if not hasattr(value, "day") or not hasattr(value, "month") or \
            not hasattr(value, "year"):
        raise ValidationError(u"{} (type {}) is no date".format(value, 
                                                                type(value)))
    if value.day != 1:
        raise ValidationError(u"{} is not the first of month".format(value))

def first_of_this_month():
    today = datetime.date.today()
    today = datetime.date(day=1, month=today.month, year=today.year)
    return today

class Currency(models.Model):
    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=32, blank=False)
    symbol = models.CharField(max_length=5, blank=False)

    def __unicode__(self):
        return "{} ({})".format(sefl.name, self.code)

class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name="budget_profile")
    language = models.CharField(max_length=2, choices=(
                                ("en", get_language_info("en")['name_local']), 
                                ("de", get_language_info("de")['name_local'])),
                                default="en")

    def __unicode__(self):
        return self.user.username

    @property
    def total_accounts_sum(self):
        return sum(account.saldo for account in self.accounts.all())

    @property
    def budget_accounts(self):
        return self.accounts.filter(on_budget=True).order_by('name')

    @property
    def budget_accounts_sum(self):
        return sum(account.saldo for account in self.budget_accounts)

    @property
    def off_budget_accounts(self):
        return self.accounts.filter(on_budget=False).order_by('name')

    @property
    def off_budget_accounts_sum(self):
        return sum(account.saldo for account in self.off_budget_accounts)


class Account(models.Model):
    TYPE_CASH           =  0
    TYPE_CHECKING       =  1
    TYPE_CREDIT_CARD    =  2
    TYPE_INVESTMENT     =  3
    TYPE_LINE_OF_CREDIT =  4
    TYPE_LOAN           =  5
    TYPE_MERCHANT       =  6
    TYPE_MORTAGE        =  7
    TYPE_P2P_WALLET     =  8
    TYPE_PAYPAL         =  8
    TYPE_SAVING         =  9
    TYPE_OTHER          = 10

    name = models.CharField(max_length=32, blank=False)
    note = models.TextField(blank=True)
    user = models.ForeignKey(UserProfile, null=False, related_name="accounts")
    type = models.IntegerField(blank=False, 
            choices=((TYPE_CASH, "Cash"), (TYPE_CHECKING, "Checking"), 
            (TYPE_CREDIT_CARD, "Credit Card"), 
            (TYPE_INVESTMENT, "Investment Account"), (TYPE_LINE_OF_CREDIT, 
            "Line of Credit"), (TYPE_LOAN, "Loan"), (TYPE_MERCHANT, 
            "Merchant Account"), (TYPE_MERCHANT, "Mortage"), 
            (TYPE_P2P_WALLET, "Peer-to-peer electronic money wallet"),
            (TYPE_PAYPAL, "Paypal"), (TYPE_SAVING, "Saving"), 
            (TYPE_OTHER, "Other")))
    line_of_credit = money_field()
    starting_balance = money_field() 
    on_budget = models.BooleanField(default=True, blank=False)

    class Meta:
        unique_together = ('name','user')

    def __unicode__(self):
        return self.name
    
    @property
    def saldo(self):
        saldo = self.starting_balance
        transactions = self.implemented_transactions.aggregate(models.Sum('outflow'),
                                                               models.Sum('inflow'))
        saldo -= transactions['outflow__sum'] or 0
        saldo += transactions['inflow__sum'] or 0
        transfers_to = self.implemented_transfers_to.aggregate(models.Sum('outflow'), 
                                                               models.Sum('inflow'))
        saldo += transfers_to['outflow__sum'] or 0 
        saldo -= transfers_to['inflow__sum'] or 0
        return saldo

    @property
    def implemented_transactions(self):
        return self.transactions.exclude(
                Q(pk__in=ScheduledTransaction.objects.values_list('transaction_ptr_id', 
                                                                  flat=True)) | \
                Q(pk__in=ScheduledTransfer.objects.values_list('transaction_ptr_id',
                                                               flat=True)))

    @property
    def implemented_transfers_to(self):
        return self.transfers_to.exclude(
                Q(pk__in=ScheduledTransfer.objects.values_list('transfer_ptr_id',
                                                               flat=True)))

class CategoryGroup(models.Model):
    name = models.CharField(max_length=32, blank=False, unique=True)
    user = models.ManyToManyField(UserProfile, related_name="category_groups")
    default = models.BooleanField(default=False, blank=False)
    budgeted = models.BooleanField(default=True, editable=False)

    def __unicode__(self):
        return u"{}".format(self.name)

class Category(models.Model):
    group = models.ForeignKey(CategoryGroup, null=False, 
                              related_name="categories")
    user = models.ManyToManyField(UserProfile, related_name="categories")
    name = models.CharField(max_length=32, primary_key=True)
    default = models.BooleanField(default=False, blank=False)
    budgeted = models.BooleanField(default=True, editable=False)

    def __unicode__(self):
        return u"{}: {}".format(self.group, self.name)

class Budget(models.Model):
    month = models.DateField(validators=[is_first_of_month], blank=False,
                             default=first_of_this_month)
    category_amounts = models.ManyToManyField(Category, through="CategoryBudget",
                                              related_name="budgets")
    user = models.ForeignKey(UserProfile, blank=False, related_name="budgets")

    class Meta:
        unique_together = ('month', 'user')

    def __unicode__(self):
        return self.month.strftime("%B %Y")

    @property
    def amount(self):
        return self.category_budget_set.aggregate(models.Sum('amount'))

    def category_group_amount(self, category_group):
        return self.category_budget_set.filter(category__group=category_group).\
                aggregate(models.Sum('amount'))

class CategoryBudget(models.Model):
    budget = models.ForeignKey(Budget, blank=False)
    category = models.ForeignKey(Category, blank=False)
    amount = money_field(validators=[validators.MinValueValidator(0)]) 

    class Meta:
        unique_together = ('category', 'budget')

    def __unicode__(self):
        return u"0.02f".format(self.amount)

class Transaction(models.Model):
    added = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(Account, null=False, 
                                related_name="transactions")
    check_nr = models.IntegerField(null=True, blank=True)
    payee = models.CharField(max_length=32)
    date = models.DateField()
    category = models.ForeignKey(Category, related_name="transactions",
                                 null=True, blank=True)
    memo = models.CharField(max_length=64, null=True, blank=True)
    inflow = money_field(validators=[validators.MinValueValidator(0)]) 
    outflow = money_field(validators=[validators.MinValueValidator(0)]) 
    cleared = models.BooleanField(default=False, blank=False)

    def is_transfer(self):
        return Transfer.objects.filter(pk=self.pk).exists()

    def as_transfer(self):
        return Transfer.objects.get(pk=self.pk)

    def __unicode__(self):
        return u"Transaction : {} <=> {}".format(self.account, self.payee)

class Transfer(Transaction):
    to_account = models.ForeignKey(Account, null=True,
                                   related_name="transfers_to",
                                   on_delete=models.SET_NULL)

    def __unicode__(self):
        return u"Transfer : {} <=> {}".format(self.account, self.to_account)
