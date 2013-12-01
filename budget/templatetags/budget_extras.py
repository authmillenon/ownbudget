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
