"""
Django models
"""
import datetime

from django.db import models
from django.db.models import Q
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
    # currency = models.ForeignKey(Currency, default="USD", blank=False)
    # currency_format = models.IntegerField(blank=False, default=0, choices=
    #                                         ((0, "{currency}{format}"),
    #                                          (1, "{currency} {format}"),
    #                                          (2, "{format}{currency}"),
    #                                          (3, "{format} {currency}")))

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
    users = models.ManyToManyField(UserProfile, related_name="category_groups",
                                   through='UserCategoryGroup')
    default = models.BooleanField(default=False, blank=False)
    budgeted = models.BooleanField(default=True, editable=False)

    def __unicode__(self):
        return self.name

class UserCategoryGroup(models.Model):
    user = models.ForeignKey(UserProfile, related_name="user_category_groups")
    category_group = models.ForeignKey(CategoryGroup, related_name="user_category_groups")
    priority = models.IntegerField(blank=False, null=False)

    def __unicode__(self):
        return unicode(self.category_group)

class Category(models.Model):
    group = models.ForeignKey(CategoryGroup, null=False, 
                              related_name="categories")
    users = models.ManyToManyField(UserProfile, related_name="categories",
                                   through="UserCategory")
    name = models.CharField(max_length=32, primary_key=True)
    default = models.BooleanField(default=False, blank=False)
    budgeted = models.BooleanField(default=True, editable=False)

    def __unicode__(self):
        return self.name

class UserCategory(models.Model):
    user = models.ForeignKey(UserProfile, related_name="user_categories")
    group = models.ForeignKey(UserCategoryGroup, related_name="user_categories")
    category = models.ForeignKey(Category, related_name="user_categories")
    priority = models.IntegerField(blank=False, null=False)

    def __unicode__(self):
        return unicode(self.category)

class IncomeCategory(Category):
    month = models.DateField(validators=[is_first_of_month], blank=False,
                             default=first_of_this_month, db_index=True)

    def save(self, *args, **kwargs):
        self.group, _ = CategoryGroup.objects.get_or_create(name="Income")
        self.name = self.month.strftime("Income for %B %Y")
        self.default = True
        self.budgeted = False
        super(Category, self).save(*args, **kwargs)

class Schedule(models.Model):
    REPEAT_DAILY    = 0
    REPEAT_WEEKLY   = 1
    REPEAT_MONTHLY  = 2
    REPEAT_YEARLY   = 3

    start_date = models.DateField(auto_now_add=True, blank=False)
    end_date = models.DateField(auto_now_add=True, blank=True, null=True)
    repeat = models.IntegerField(blank=False, default=REPEAT_MONTHLY, 
                                 choices=((REPEAT_DAILY, "daily"), 
                                        (REPEAT_WEEKLY, "weekly"),
                                        (REPEAT_MONTHLY, "monthly"),
                                        (REPEAT_YEARLY, "yearly")))
    interval = models.IntegerField(blank=False, default=1,
                                   validators=[validators.MinValueValidator(1)])

    class Meta:
        unique_together = ('start_date', 'end_date', 'repeat', 'interval')

class WeeklySchedule(Schedule):
    mondays = models.BooleanField(default=today_is_the_day(0), blank=False)
    tuesdays = models.BooleanField(default=today_is_the_day(1), blank=False)
    wednesdays = models.BooleanField(default=today_is_the_day(2), blank=False)
    thursdays = models.BooleanField(default=today_is_the_day(3), blank=False)
    fridays = models.BooleanField(default=today_is_the_day(4), blank=False)
    saturdays = models.BooleanField(default=today_is_the_day(5), blank=False)
    sundays = models.BooleanField(default=today_is_the_day(6), blank=False)

class MonthlySchedule(Schedule):
    REPEAT_AT_DOM = False
    REPEAT_AT_DOW = True

    repeat_on = models.BooleanField(default=REPEAT_AT_DOM, blank=False,
                                    choices=((False, "day of month"),
                                             (True, "day of week")))

class Budget(models.Model):
    month = models.DateField(validators=[is_first_of_month], blank=False,
                             default=first_of_this_month)
    categories = models.ManyToManyField(Category, through="CategoryBudget",
                                        related_name="budgets")
    user = models.ForeignKey(UserProfile, blank=False, related_name="budgets")

    class Meta:
        unique_together = ('month', 'user')

    def __unicode__(self):
        return self.month.strftime("%B %Y")

    @property
    def amount(self):
        return self.category_budget.filter(category__budgeted=True).\
                aggregate(models.Sum('amount'))['amount__sum'] or 0

    @property
    def income(self):
        ic, created = IncomeCategory.objects.get_or_create(month=self.month, budgeted=False)
        transactions = ic.transactions.filter(account__user=self.user).aggregate(
                models.Sum('inflow'), models.Sum('outflow'))
        inflow = transactions['inflow__sum'] or 0
        outflow = transactions['outflow__sum'] or 0
        return inflow-outflow
    
    def get_last_month_budget(self):
        if self.month.month == 1:
            last_month = Budget.objects.get(user=self.user,
                                            month__month=12,
                                            month__year=self.month.year - 1)
        else:
            last_month = Budget.objects.get(user=self.user,
                                            month__month=self.month.month - 1,
                                            month__year=self.month.year)
        return last_month

    @property
    def last_available(self):
        try:
            return self.get_last_month_budget().available
        except Budget.DoesNotExist:
            return 0

    def last_balance(self, category):
        try:
            return self.get_last_month_budget().balance(category)
        except Budget.DoesNotExist:
            return 0

    @property
    def last_overspend(self):
        try:
            return sum(c.balance for c in self.get_last_month().category_budget.all() \
                    if c.balance < 0)
        except Budget.DoesNotExist:
            return 0

    @property
    def available(self):
        return self.last_available + self.last_overspend + self.income - \
                self.amount

    def outflows(self, category=None):
        if category == None:
            return sum(c.outflows for c in self.category_budget.filter(category__budgeted=True))
        elif not category.budgeted:
            return 0
        else:
            try:
                return self.category_budget.get(category=category).outflows
            except CategoryBudget.DoesNotExist:
                return 0

    def balance(self, category=None):
        if category == None:
            return self.amount+self.outflows()+self.last_balance
        elif not category.budgeted:
            return 0
        else:
            try:
                last_month = self.last_balance(category)
                if last_month > 0:
                    return self.category_budget.get(category=category).balance +\
                            last_month
                else:
                    return self.category_budget.get(category=category).balance
            except CategoryBudget.DoesNotExist:
                return 0

    def category_group_amount(self, category_group):
        return self.category_budget.filter(category__group=category_group).\
                aggregate(models.Sum('amount'))['amount__sum'] or 0

    def category_group_outflows(self, category_group):
        return sum(c.outflows for c in \
                self.category_budget.filter(category__group=category_group))

    def category_group_balance(self, category_group):
        return self.category_group_amount(category_group) + \
                self.category_group_outflows(category_group)

class CategoryBudget(models.Model):
    budget = models.ForeignKey(Budget, blank=False, related_name="category_budget")
    category = models.ForeignKey(Category, blank=False, related_name="+")
    amount = money_field(validators=[validators.MinValueValidator(0)]) 
    prev_month_budget = models.ForeignKey('CategoryBudget', blank=True, null=True,
                                          default=None, related_name="next_month_budget")

    class Meta:
        unique_together = ('category', 'budget')

    def __unicode__(self):
        return u"0.02f".format(self.amount)

    @property
    def outflows(self):
        transactions = self.category.transactions.filter(
                account__user=self.budget.user, account__on_budget=True, 
                date__month=self.budget.month.month,
                date__year=self.budget.month.year).aggregate(
                models.Sum('inflow'), models.Sum('outflow'))
        inflow = transactions['inflow__sum'] or 0
        outflow = transactions['outflow__sum'] or 0
        return inflow-outflow

    @property
    def balance(self):
        if self.prev_month_budget == None:
            return self.amount+self.outflows
        else:
            return self.amount+self.outflows+self.prev_month_budget.balance

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

class ScheduledTransaction(Transaction):
    schedule = models.ForeignKey(Schedule, null=False, related_name="+", 
                                 on_delete=models.PROTECT)
    implemented = models.ManyToManyField(Transaction, null=False, 
                                         related_name="generated_by")

class ScheduledTransfer(Transfer, ScheduledTransaction):
    pass
