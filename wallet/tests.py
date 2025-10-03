import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APITestCase, APIClient

from wallet.models import Wallet
from wallet.serializers import WalletSerializer, WalletOperationSerializer


class WalletModelTests(TestCase):
    """Проверяем модель класса Wallet"""
    def setUp(self):
        """Создаем объект класса Wallet"""
        self.wallet = Wallet.objects.create()

    def test_wallet_creation(self):
        """Проверяем создание кошелька.

        проверяем:
        -экзампляр нужного класса
        -значение по умолчанию
        -существование агумента времени и id
        """
        self.assertTrue(isinstance(self.wallet, Wallet))
        self.assertEqual(self.wallet.amount, Decimal(0.00))
        self.assertIsNotNone(self.wallet.at_create)
        self.assertIsNotNone(self.wallet.time_update)
        self.assertIsNotNone(self.wallet.id)

    def test_amount_negative(self):
        """Проверка на то что балланс не может быть отрицательным"""
        self.wallet.amount = Decimal('-1512.00')
        with self.assertRaises(Exception):
            self.wallet.full_clean()


class SerializerTests(TestCase):
    """Проверяем работу сериализатора"""

    def test_wallet_serializer(self):
        """Тест сериализатора кошелька"""
        wallet = Wallet.objects.create(amount=Decimal('1000.00'))
        serializer = WalletSerializer(wallet)

        self.assertEqual(serializer.data['id'], str(wallet.id))
        self.assertEqual(serializer.data['amount'], '1000.00')
        self.assertIsNotNone('at_created', serializer.data)
        self.assertIsNotNone('time_update', serializer.data)

    def test_valid_date(self):
        """Проверка на валидность данных"""
        valid_date = {
            "operation_type": "DEPOSIT",
            "amount": "100.00"
        }
        serializer_test = WalletOperationSerializer(data=valid_date)
        self.assertTrue(serializer_test.is_valid())

    def test_invalid_data(self):
        """Проверка на невалидность данных"""
        invalid_date_operating_type = {
            "operation_type": "Чушь",
            "amount": "1000.00"
        }
        serializer = WalletOperationSerializer(data=invalid_date_operating_type)
        self.assertFalse(serializer.is_valid())
        self.assertIn('operation_type', serializer.errors)

        invalid_date_amount = {
            "operation_type": "DEPOSIT",
            "amount": "-100.00"
        }

        serializer = WalletOperationSerializer(data=invalid_date_amount)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)

    def test_zero_amount_operation(self):
        invalid_date_zero_amount = {
            "operation_type": "DEPOSIT",
            "amount": "0.00"
        }

        serializer = WalletOperationSerializer(data=invalid_date_zero_amount)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)


class WalletAPITests(APITestCase):
    """Проврка на API и эндпоиты"""
    def setUp(self):
        """Создаем операции и APIClient"""
        self.client = APIClient()
        self.wallet = Wallet.objects.create()
        self.operation_url = reverse('wallet:wallet_operation', kwargs={'wallet_uuid': self.wallet.id})
        self.operation_amount = reverse('wallet:wallet_amount', kwargs={'wallet_uuid': self.wallet.id})

    def test_get_wallet(self):
        """Проверка на существующий кошелек"""
        response = self.client.get(self.operation_amount)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.wallet.id))
        self.assertEqual(response.data['amount'], '0.00')

    def test_get_non_wallet(self):
        """Проверка на несуществующий кошелек"""
        non_wallet = uuid.uuid4()
        operation_amount_non = reverse('wallet:wallet_amount', kwargs={'wallet_uuid': non_wallet})

        response = self.client.get(operation_amount_non)

        if response.status_code != 404:
            print(f"Get non-wallet error: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deposit(self):
        """Проверяем способность пополнения кошелька """

        operations = [
            {'operation_type': 'DEPOSIT', 'amount': '100.00'},
            {'operation_type': 'DEPOSIT', 'amount': '200.00'},
            {'operation_type': 'DEPOSIT', 'amount': '300.00'},
        ]

        for operation in operations:
            response = self.client.post(self.operation_url, operation, format="json")
            if response.status_code != 200:
                print(f"Deposit error: {response.data}")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.amount, Decimal('600.00'))

    def test_withdraw(self):
        """Проверяем работу снятия средств"""

        deposit_operations = {'operation_type': 'DEPOSIT', 'amount': '600.00'}

        response = self.client.post(self.operation_url, deposit_operations, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        operations = [
            {'operation_type': 'WITHDRAW', 'amount': '100.00'},
            {'operation_type': 'WITHDRAW', 'amount': '100.00'},
            {'operation_type': 'WITHDRAW', 'amount': '100.00'},
        ]

        for operation in operations:
            response = self.client.post(self.operation_url, operation, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.amount, Decimal('300.00'))

    def test_withdraw_over_amount(self):
        """Проверки снятия сверх доступных средств"""

        self.assertEqual(self.wallet.amount, Decimal('0.00'))

        operation = {'operation_type': 'WITHDRAW', 'amount': '400.00'},

        response = self.client.post(self.operation_url, operation, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

