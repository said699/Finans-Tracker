from django.db import models
from django.core.validators import RegexValidator
from django.conf import settings

hex_color_validator = RegexValidator(regex="^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$",
                                    message="Введите корректный HEX-код цвета")

class PayCategory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Владелец категории')
    name = models.CharField(max_length=100, verbose_name='Название категории')
    color = models.CharField(max_length=7, validators=[hex_color_validator], verbose_name='Цвет категории')


class Payment(models.Model):
    CURRENCY_CHOICES = [
        ('USD', 'USD ($)'),
        ('EUR', 'EUR (€)'),
        ('RUB', 'RUB (₽)'),
        ('UZS', 'UZS (сум)'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Плательщик')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма платежа')
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, verbose_name='Валюта платежа')
    category = models.ForeignKey(PayCategory, null=True, on_delete=models.SET_NULL, verbose_name='Категория платежа')
    date_done = models.DateTimeField(auto_now_add=True, verbose_name='Дата платежа')