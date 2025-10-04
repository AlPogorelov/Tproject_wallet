from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

from rest_framework.exceptions import ValidationError


class Wallet(models.Model):
    """
    Класс "платеж".
        Должен иметь:
    индификатор,
    баланс,
    дата последнего обновления (контроль актуальности и фиксации времени)
    когда была создан

    """
    OPERATIONS_TYPE = [
        ('DEPOSIT', 'Пополнение'),
        ('WITHDRAW', 'Снятие'),
    ]

    id = models.UUIDField(primary_key=True,
                          default=uuid.uuid4,
                          verbose_name='UUID индификатор',
                          unique=True,
                          editable=False)

    amount = models.DecimalField(decimal_places=2,
                                 max_digits=15,
                                 verbose_name='Баланc кошелька',
                                 default=Decimal('0.00'),
                                 validators=[MinValueValidator(Decimal('0.00'))]
                                 )

    time_update = models.DateTimeField(verbose_name='Дата и время последнего обновления',
                                       auto_now_add=True)

    at_create = models.DateTimeField(auto_now=True,
                                     verbose_name='дата создания кошелька')

    class Meta:
        db_table = 'wallets'
        verbose_name = 'Кошелек'
        verbose_name_plural = 'Кошельки'
        ordering = ['-time_update']

    def clean(self):
        """Проверка аргумента "баланс" перед сохарнением"""
        if self.amount < Decimal('0.00'):
            raise ValidationError({'amount': 'Баланс не может быть отрицательным'})

    def save(self, *args, **kwargs):
        """Делаем так, чтобы перед сохранением автоматической валидации """
        self.full_clean()  # Вызывает clean() и валидаторы полей
        super().save(*args, **kwargs)
