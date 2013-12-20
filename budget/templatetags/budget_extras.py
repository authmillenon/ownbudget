import calendar, datetime

from django import template
from django.template.defaulttags import TemplateIfParser
from django.template.defaultfilters import add

register = template.Library()

@register.filter
def sub(value, arg):
    try:
        return int(value)-int(arg)
    except (ValueError, TypeError):
        try:
            return value - arg
        except Exception:
            return ''

@register.filter
def month_sub(value, arg):
    if isinstance(value, datetime.date):
        try:
            arg = int(arg)
            months = value.month - arg
            if months > 0:
                return datetime.date(year=value.year,
                                     month=months, 
                                     day=value.day)
            else:
                years = months//12
                months = months % 12 or 12
                return datetime.date(year=value.year+years,
                                     month=months, 
                                     day=value.day)
        except (ValueError, TypeError):
            pass
    result = sub(value, arg)
    if isinstance(result, int):
        return result % 12 or 12
    else:
        return result

@register.filter
def month_add(value, arg):
    if isinstance(value, datetime.date):
        try:
            arg = int(arg)
            months = value.month + arg
            if months <= 12:
                return datetime.date(year=value.year,
                                     month=months, 
                                     day=value.day)
            else:
                years = months//12
                months = months % 12 or 12
                return datetime.date(year=value.year+years,
                                     month=months, 
                                     day=value.day)
        except (ValueError, TypeError):
            pass
    result = add(value, arg)
    if isinstance(result, int):
        return result % 12 or 12
    else:
        return result

@register.simple_tag
def month_abbr(value):
    try:
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.strftime("%b")
        return calendar.month_abbr[int(value)]
    except (ValueError, TypeError, IndexError):
        return ''

@register.filter
def category_field(form, category):
    try:
        return form[category]
    except (ValueError, IndexError):
        return ''

class SetMonthBudgetNode(template.Node):
    def render(self, context):
        try:
            user = context['user'].budget_profile
            form = context['form']
        except KeyError:
            return ''
        try:
            context['month_budget'] = form.initial['budget']
        except KeyError:
            if len(form.prefix) > 0:
                budget_id = int(form.data[form.prefix+'-budget'][0])
            else:
                budget_id = int(form.data['budget'][0])
            context['month_budget'] = user.budgets.get(id=budget_id)
        return ''

@register.tag
def set_month_budget(parser, token):
    return SetMonthBudgetNode()

class BudgetValueNode(template.Node):
    def __init__(self, value):
        self.value = value

    def render(self, context):
        if self.value == 'group_amount':
            ret = context['month_budget'].category_group_amount(context['user_category'].category.group)
        elif self.value == 'group_outflows':
            ret = context['month_budget'].category_group_outflows(context['user_category'].category.group)
        elif self.value == 'group_balance':
            ret = context['month_budget'].category_group_balance(context['user_category'].category.group)
        elif self.value == 'outflows':
            ret = context['month_budget'].outflows(context['user_category'].category)
        elif self.value == 'balance':
            ret = context['month_budget'].balance(context['user_category'].category)
        else:
            return ''
        if ret < 0 and 'balance' in self.value:
            return "<span class=\"text-danger\">{:0.2f}</span>".format(ret)
        else:
            return "{:0.2f}".format(ret)

@register.tag
def budget_value(parser, token):
    try:
        tag_name, value = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires exactly two arguments" % token.contents.split()[0])
    return BudgetValueNode(value)            
