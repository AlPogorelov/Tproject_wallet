from rest_framework import serializers
from decimal import Decimal
from wallet.models import Wallet


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ["id", "amount"]
        read_only_fields = ["id", "amount", "time_update", "at_create"]


class WalletOperationSerializer(serializers.Serializer):
    """Сериализатор операции над кошельком. Получаем через POST запрос. Проверяем на валидность"""
    OPERATION_TYPES = (
        ('DEPOSIT', 'Пополнение'),
        ('WITHDRAW', 'Снятие'),
    )

    operation_type = serializers.ChoiceField(choices=OPERATION_TYPES)
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0.01'))

    def validate_amount(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("Сумма должна быть положительной")
        return value
