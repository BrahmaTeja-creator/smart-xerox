# smartprint/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(value, arg):
    """
    Adds a CSS class to a form field.
    Usage: {{ field|add_class:"my-class" }}
    """
    return value.as_widget(attrs={'class': arg})

@register.filter(name='split')
def split_string(value, arg):
    """
    Splits a string by the given argument.
    Usage: {{ value|split:"/" }}
    """
    return value.split(arg)