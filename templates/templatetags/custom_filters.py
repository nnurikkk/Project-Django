from django import template

register = template.Library()

@register.filter
def div(value, arg):
    """Divide the value by the argument"""
    try:
        return float(value) / float(arg) if arg else 0
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def percentage(value, arg):
    """Calculate percentage: (value/arg)*100"""
    try:
        return (float(value) / float(arg)) * 100 if arg else 0
    except (ValueError, ZeroDivisionError):
        return 0