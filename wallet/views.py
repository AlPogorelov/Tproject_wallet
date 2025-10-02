from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response

from wallet.models import Wallet
from wallet.serializers import WalletSerializer, WalletOperationSerializer


class WalletDetailAPIView(APIView):
    """Get запрос, отпрвляем UUID кошелька, получаем """
    def get(self, request, wallet_uuid):
        try:
            wallet = get_object_or_404(Wallet, pk=wallet_uuid)
            serializer = WalletSerializer(wallet)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Ошибка при получении кошелька: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WalletOperationsAPIView(APIView):
    """POST запрос, получаем json операции, по тому какая операция проходит бизнес логика.

    Валидация UUID кошелька, а так же формата UUID.

    """
    @transaction.atomic
    def post(self, request, wallet_uuid):
        try:
            wallet = Wallet.objects.get(id=wallet_uuid)

        except Wallet.DoesNotExist:
            return Response(
                {'error': 'Кошелек не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        except ValueError:
            return Response(
                {'error': 'Неверный формат UUID кошелька'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = WalletOperationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        operation_type = serializer.validated_data['operation_type']
        amount = serializer.validated_data['amount']

        try:
            if operation_type == 'DEPOSIT':
                wallet.amount += amount
                wallet.save()
                response_message = "Кошелек пополнен"

            elif operation_type == 'WITHDRAW':
                if wallet.amount < amount:
                    return Response(
                        {'error': 'Недостаточно средств на счете'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                wallet.amount -= amount
                wallet.save()
                response_message = "Средства успешно сняты"

            wallet.refresh_from_db()
            response_serializer = WalletSerializer(wallet)
            return Response({
                'status': response_message,
                'wallet': response_serializer.data
            })

        except Exception as e:
            return Response(
                {'error': f'Ошибка при выполнении операции: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )