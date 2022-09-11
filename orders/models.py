from django.core.exceptions import ValidationError
from django.db import models


def validate_positive_number(value):
    if value < 0:
        raise ValidationError(f"Значение {value} не является положительным!")


class Order(models.Model):
    """Заказ."""
    id = models.IntegerField(primary_key=True, unique=True)
    number = models.IntegerField(verbose_name="Номер заказа")
    dollar_cost = models.IntegerField(verbose_name="Стоимость, $", validators=[validate_positive_number])
    ruble_cost = models.IntegerField(verbose_name="Стоимость, руб", blank=True, null=True)
    delivery_time = models.DateField(verbose_name="Срок поставки")


class DollarRate(models.Model):
    """Курс доллара."""
    date = models.DateField(verbose_name="Дата")
    rate = models.FloatField(verbose_name="Стоимость")


class UpdateTableInfo(models.Model):
    """Информация по обновлению таблицы."""
    last_update = models.DateTimeField(verbose_name="Последнее время обновления")
