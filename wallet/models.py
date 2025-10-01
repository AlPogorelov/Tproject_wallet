from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class RecentChangeWallet(models.Model):
    """
    Класс "Последнее изменение кошелька"
    Будет хранить в себе инфомарцию о последнем изменении кошелька

    """
    at_data = models.DateTimeField(verbose_name='дата посленего изменения')
    type_operation = models.TextField()


class Wallet(models.Model):
    """
    Класс "платеж".
        Должен иметь:
    индификатор,
    баланс,
    дата последнего обновления (контроль актуальности и фиксации времени)

    """
    OPERATIONS_TYPE = [
        ('DEPOSIT', 'Пополнение'),
        ('WITHDRAW', 'Снятие'),
    ]

    id = models.UUIDField(primary_key=True,
                          verbose_name='UUID индификатор',
                          unique=True)

    amount = models.DecimalField(decimal_places=15,
                                 max_digits=2,
                                 verbose_name='Баланc кошелька',
                                 default=Decimal('0.00'),
                                 validators=[MinValueValidator(Decimal('0.00'))]
                                 )

    time_update = models.DateTimeField(verbose_name ='Дата и время последнего обновления',
                                       auto_now_add=True)

    recent_charge = models.ForeignKey(RecentChangeWallet,
                                      on_delete=models.CASCADE,
                                      verbose_name ='экзамепляр класса с описанием последнего изменения'
                                      )

    at_create = models.DateTimeField(auto_now=True,
                                     verbose_name='дата создания кошелька')

    class Meta:
        db_table = 'wallets'
        verbose_name = 'Кошелек'
        verbose_name_plural = 'Кошельки'
        ordering = ['-time_update']
