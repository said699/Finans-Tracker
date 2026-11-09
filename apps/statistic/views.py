from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from . import get_statistic
from apps.finans.models import Earnings, Payment

MONTHS = [
    (1, "Январь"), (2, "Февраль"), (3, "Март"), (4, "Апрель"),
    (5, "Май"), (6, "Июнь"), (7, "Июль"), (8, "Август"),
    (9, "Сентябрь"), (10, "Октябрь"), (11, "Ноябрь"), (12, "Декабрь"),
]


@login_required
def statistics(request):
    now = timezone.localtime()

    # год и месяц из адреса: /stats/?year=2026&month=11 (по умолчанию текущие)
    try:
        year = int(request.GET.get("year", now.year))
        month = int(request.GET.get("month", now.month))
    except ValueError:
        year, month = now.year, now.month
    if not 1 <= month <= 12:
        month = now.month

    user = request.user

    context = {
        "year": year,
        "month": month,
        "years": get_statistic.available_years(user) or [now.year],
        "months": MONTHS,
        "top_pay_category": get_statistic.most_used_category(user, Payment, year, month),
        "top_earn_category": get_statistic.most_used_category(user, Earnings, year, month),
        "spent_month": get_statistic.total_by_currency(user, Payment, year, month),
        "spent_year": get_statistic.total_by_currency(user, Payment, year),
        "balance": get_statistic.balance(user, year, month),
        "breakdown": get_statistic.category_breakdown(user, Payment, year, month),
    }
    return render(request, "statistic/stats.html", context)