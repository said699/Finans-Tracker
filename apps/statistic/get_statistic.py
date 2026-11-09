import calendar
from collections import defaultdict
from decimal import Decimal
from django.db.models import Avg, Count, Max, Sum
from django.db.models.functions import ExtractWeekDay, TruncMonth
from django.utils import timezone
from apps.finans.models import Earnings, Payment


def _period(qs, year=None, month=None):
    """Фильтр по году и/или месяцу. Без аргументов вернёт всё время."""
    if year:
        qs = qs.filter(date_done__year=year)
        if month:
            qs = qs.filter(date_done__month=month)
    return qs


# 1. Самая используемая категория (по числу записей)
def most_used_category(user, model=Payment, year=None, month=None):
    qs = _period(model.objects.filter(user=user, category__isnull=False), year, month)
    return (
        qs.values("category__name", "category__color")
        .annotate(n=Count("id"))
        .order_by("-n", "category__name")
        .first()
    )  # {'category__name': 'Еда', 'category__color': '#FF0000', 'n': 12} или None


# 2. Сколько потрачено за год/месяц (отдельно по каждой валюте)
def total_by_currency(user, model=Payment, year=None, month=None):
    rows = (
        _period(model.objects.filter(user=user), year, month)
        .values("currency")
        .annotate(total=Sum("amount"))
    )
    return {r["currency"]: r["total"] for r in rows}  # {'USD': Decimal('120.50'), 'UZS': ...}


# 3. Итоги по месяцам года (для графика)
def monthly_totals(user, year, model=Payment):
    rows = (
        model.objects.filter(user=user, date_done__year=year)
        .annotate(month=TruncMonth("date_done"))
        .values("month", "currency")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )
    result = defaultdict(dict)  # {1: {'USD': Decimal}, 2: {...}}
    for r in rows:
        result[r["month"].month][r["currency"]] = r["total"]
    return dict(result)


# 4. Расходы по категориям (для круговой диаграммы)
def category_breakdown(user, model=Payment, year=None, month=None):
    rows = (
        _period(model.objects.filter(user=user), year, month)
        .values("currency", "category__name", "category__color")
        .annotate(total=Sum("amount"), n=Count("id"))
        .order_by("currency", "-total")
    )
    result = defaultdict(list)
    for r in rows:
        result[r["currency"]].append({
            "name": r["category__name"] or "Без категории",
            "color": r["category__color"] or "#999999",
            "total": r["total"],
            "count": r["n"],
        })
    return dict(result)


# 5. Баланс: доходы минус расходы
def balance(user, year=None, month=None):
    income = total_by_currency(user, Earnings, year, month)
    spent = total_by_currency(user, Payment, year, month)
    return {
        cur: income.get(cur, Decimal("0")) - spent.get(cur, Decimal("0"))
        for cur in set(income) | set(spent)
    }


# 6. Средняя и максимальная сумма, количество записей
def basic_stats(user, model=Payment, year=None, month=None):
    rows = (
        _period(model.objects.filter(user=user), year, month)
        .values("currency")
        .annotate(avg=Avg("amount"), max=Max("amount"), n=Count("id"))
    )
    return {r["currency"]: {"avg": r["avg"], "max": r["max"], "count": r["n"]} for r in rows}


# 7. Сколько тратишь в день в среднем за месяц
def average_per_day(user, year, month, model=Payment):
    now = timezone.localtime()
    days = now.day if (now.year, now.month) == (year, month) else calendar.monthrange(year, month)[1]
    return {cur: total / days for cur, total in total_by_currency(user, model, year, month).items()}


# 8. Топ-N самых крупных записей
def top_transactions(user, model=Payment, year=None, month=None, limit=5):
    return list(
        _period(model.objects.filter(user=user), year, month)
        .select_related("category")
        .order_by("-amount")[:limit]
    )


# 9. Сравнение с предыдущим месяцем (в процентах)
def compare_with_previous_month(user, year, month, model=Payment):
    prev_year, prev_month = (year, month - 1) if month > 1 else (year - 1, 12)
    current = total_by_currency(user, model, year, month)
    previous = total_by_currency(user, model, prev_year, prev_month)
    result = {}
    for cur, total in current.items():
        old = previous.get(cur)
        result[cur] = float((total - old) / old * 100) if old else None  # None = не с чем сравнивать
    return result


# 10. В какой день недели тратишь больше всего (1 = воскресенье ... 7 = суббота)
def weekday_stats(user, model=Payment, year=None, month=None):
    rows = (
        _period(model.objects.filter(user=user), year, month)
        .annotate(wd=ExtractWeekDay("date_done"))
        .values("wd", "currency")
        .annotate(total=Sum("amount"))
        .order_by("wd")
    )
    return list(rows)


# 11. Годы, за которые есть записи (для выпадающего списка)
def available_years(user, model=Payment):
    return sorted(
        set(model.objects.filter(user=user).order_by().values_list("date_done__year", flat=True)),
        reverse=True,
    )