import calendar
from django import template

register = template.Library()

@register.filter
def to_list(start, end):
    return list(range(start, end + 1))

@register.filter
def date_calendar(ym):
    try:
        year, month = map(int, ym.split('-'))
        cal = calendar.Calendar(firstweekday=6)
        weeks = cal.monthdatescalendar(year, month)
        while len(weeks) < 6:
            weeks.append([None] * 7)
        return weeks
    except Exception:
        return []

@register.filter
def pluck(queryset, attr):
    return [getattr(obj, attr) for obj in queryset]

@register.filter
def contains(value, arg):
    return arg in value

@register.filter
def index(sequence, i):
    try:
        return sequence[i - 1]  # Adjusting 1-based month to 0-based index
    except:
        return ""