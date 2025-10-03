import threading
import uuid
import time
import atexit
from django.db import transaction, connections
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APITestCase, APIClient

from wallet.models import Wallet
from wallet.serializers import WalletSerializer, WalletOperationSerializer


class DatabaseCleanupMixin:
    """Миксин для очистки соединений с БД после тестов"""
    def tearDown(self):
        super().tearDown()
        connections.close_all()


def close_all_connections():
    """Функция для закрытия всех соединений с БД"""
    for conn in connections.all():
        conn.close()


atexit.register(close_all_connections)


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


class WalletConcurrentTests(TransactionTestCase, DatabaseCleanupMixin):
    """Проверяем конкурентную среду"""
    def setUp(self):
        """Создаем операции и APIClient"""
        with transaction.atomic():
            self.wallet = Wallet.objects.create(amount=Decimal('1000.00'))
        self.operation_url = reverse('wallet:wallet_operation', kwargs={'wallet_uuid': self.wallet.id})
        self.operation_amount = reverse('wallet:wallet_amount', kwargs={'wallet_uuid': self.wallet.id})

    def test_concurrent_deposits(self):
        """Тест конкурентных пополнений кошелька"""
        initial_amount = self.wallet.amount
        deposit_amount = Decimal('100.00')
        num_threads = 5
        expected_final_amount = initial_amount + (deposit_amount * num_threads)

        def deposit_operation():
            from django.db import connection
            try:
                client = APIClient()
                operation = {
                    'operation_type': 'DEPOSIT',
                    'amount': '100.00'
                }
                response = client.post(self.operation_url, operation, format="json")
                if response.status_code != 200:
                    print(f"Deposit error in thread: {response.data}")
            except Exception as e:
                print(f"Exception in thread: {str(e)}")
            finally:
                connection.close()

        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=deposit_operation, name=f"DepositThread-{i}")
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        time.sleep(0.5)

        self.wallet.refresh_from_db()
        self.assertEqual(
            self.wallet.amount,
            expected_final_amount,
            f"Ожидалось: {expected_final_amount}, получено: {self.wallet.amount}")

    def test_concurrent_withdrawals(self):
        """Тест конкурентных списаний с кошелька"""
        with transaction.atomic():
            self.wallet.amount = Decimal('1000.00')
            self.wallet.save()

        withdrawal_amount = Decimal('100.00')
        num_threads = 5
        expected_final_amount = Decimal('1000.00') - (withdrawal_amount * num_threads)

        def withdraw_operation():
            from django.db import connection
            try:
                client = APIClient()
                operation = {
                    'operation_type': 'WITHDRAW',
                    'amount': '100.00'
                }
                response = client.post(self.operation_url, operation, format="json")
                if response.status_code != 200:
                    print(f"Withdraw error in thread: {response.data}")
            except Exception as e:
                print(f"Exception in thread: {str(e)}")
            finally:
                connection.close()

        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=withdraw_operation, name=f"WithdrawThread-{i}")
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        time.sleep(0.5)
        self.wallet.refresh_from_db()
        self.assertEqual(
            self.wallet.amount,
            expected_final_amount,
            f"Ожидалось: {expected_final_amount}, получено: {self.wallet.amount}")

    # def test_race_condition_withdraw(self):
    #     """Тест состояния гонки при списании - только один должен пройти"""
    #     # Устанавливаем маленький баланс
    #     with transaction.atomic():
    #         self.wallet.amount = Decimal('300.00')
    #         self.wallet.save()
    #
    #     results = []
    #     results_lock = threading.Lock()
    #
    #     def withdraw_operation(thread_id):
    #         client = APIClient()
    #         operation = {
    #             'operation_type': 'WITHDRAW',
    #             'amount': '200.00'
    #         }
    #         try:
    #             response = client.post(self.operation_url, operation, format="json")
    #             with results_lock:
    #                 results.append({
    #                     'thread_id': thread_id,
    #                     'status_code': response.status_code,
    #                     'data': response.data if hasattr(response, 'data') else str(response)
    #                 })
    #         except Exception as e:
    #             with results_lock:
    #                 results.append({
    #                     'thread_id': thread_id,
    #                     'error': str(e)
    #                 })
    #
    #     threads = []
    #     num_threads = 3
    #
    #     for i in range(num_threads):
    #         thread = threading.Thread(target=withdraw_operation, args=(i,), name=f"RaceThread-{i}")
    #         threads.append(thread)
    #
    #     for thread in threads:
    #         thread.start()
    #
    #     for thread in threads:
    #         thread.join()
    #
    #     time.sleep(0.5)
    #     self.wallet.refresh_from_db()
    #
    #     success_count = sum(1 for r in results if r.get('status_code') == 200)
    #     error_count = sum(1 for r in results if r.get('status_code') == 400)
    #
    #     self.assertEqual(success_count, 1, f"Должен быть только один успешный запрос. Результаты: {results}")
    #     self.assertEqual(self.wallet.amount, Decimal('100.00'))
    #
    # def test_concurrent_mixed_operations(self):
    #     """Тест смешанных операций в конкурентной среде"""
    #     with transaction.atomic():
    #         self.wallet.amount = Decimal('500.00')
    #         self.wallet.save()
    #
    #     results = []
    #     results_lock = threading.Lock()
    #
    #     def deposit_operation(thread_id):
    #         client = APIClient()
    #         operation = {
    #             'operation_type': 'DEPOSIT',
    #             'amount': '100.00'
    #         }
    #         try:
    #             response = client.post(self.operation_url, operation, format="json")
    #             with results_lock:
    #                 results.append({
    #                     'thread_id': thread_id,
    #                     'type': 'DEPOSIT',
    #                     'status_code': response.status_code
    #                 })
    #         except Exception as e:
    #             with results_lock:
    #                 results.append({
    #                     'thread_id': thread_id,
    #                     'type': 'DEPOSIT',
    #                     'error': str(e)
    #                 })
    #
    #     def withdraw_operation(thread_id):
    #         client = APIClient()
    #         operation = {
    #             'operation_type': 'WITHDRAW',
    #             'amount': '50.00'
    #         }
    #         try:
    #             response = client.post(self.operation_url, operation, format="json")
    #             with results_lock:
    #                 results.append({
    #                     'thread_id': thread_id,
    #                     'type': 'WITHDRAW',
    #                     'status_code': response.status_code
    #                 })
    #         except Exception as e:
    #             with results_lock:
    #                 results.append({
    #                     'thread_id': thread_id,
    #                     'type': 'WITHDRAW',
    #                     'error': str(e)
    #                 })
    #
    #     threads = []
    #
    #     for i in range(3):
    #         deposit_thread = threading.Thread(target=deposit_operation, args=(i,), name=f"MixedDeposit-{i}")
    #         withdraw_thread = threading.Thread(target=withdraw_operation, args=(i + 3,), name=f"MixedWithdraw-{i + 3}")
    #         threads.extend([deposit_thread, withdraw_thread])
    #
    #     for thread in threads:
    #         thread.start()
    #
    #     for thread in threads:
    #         thread.join()
    #
    #     time.sleep(0.5)
    #     self.wallet.refresh_from_db()
    #
    #     expected_amount = Decimal('650.00')
    #     self.assertEqual(self.wallet.amount, expected_amount,
    #                      f"Ожидалось: {expected_amount}, получено: {self.wallet.amount}. Результаты: {results}")


class WalletModelConcurrentTests(TransactionTestCase, DatabaseCleanupMixin):
    """Тесты модели в конкурентной среде"""

    def setUp(self):
        with transaction.atomic():
            self.wallet = Wallet.objects.create(amount=Decimal('1000.00'))

    def test_concurrent_atomic_updates(self):
        """Тест атомарных обновлений через F()"""
        num_threads = 10
        barrier = threading.Barrier(num_threads)

        def update_wallet(thread_id):
            barrier.wait()

            try:
                with transaction.atomic():
                    wallet = Wallet.objects.select_for_update().get(id=self.wallet.id)
                    wallet.amount += Decimal('100.00')
                    wallet.save()
            except Exception as e:
                print(f"Error in thread {thread_id}: {str(e)}")

        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=update_wallet, args=(i,), name=f"ModelThread-{i}")
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        time.sleep(0.5)
        self.wallet.refresh_from_db()

        expected_amount = Decimal('2000.00')
        self.assertEqual(self.wallet.amount, expected_amount)


class SimpleConcurrentTests(TransactionTestCase, DatabaseCleanupMixin):
    """Упрощенные тесты для отладки"""

    def setUp(self):
        with transaction.atomic():
            self.wallet = Wallet.objects.create(amount=Decimal('1000.00'))
        self.operation_url = reverse('wallet:wallet_operation', kwargs={'wallet_uuid': self.wallet.id})

    def test_single_deposit(self):
        """Простой тест одного пополнения"""
        client = APIClient()
        operation = {
            'operation_type': 'DEPOSIT',
            'amount': '100.00'
        }
        response = client.post(self.operation_url, operation, format="json")
        self.assertEqual(response.status_code, 200)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.amount, Decimal('1100.00'))

    def test_two_sequential_deposits(self):
        """Тест двух последовательных пополнений"""
        client = APIClient()

        # Первое пополнение
        operation1 = {'operation_type': 'DEPOSIT', 'amount': '100.00'}
        response1 = client.post(self.operation_url, operation1, format="json")
        self.assertEqual(response1.status_code, 200)

        # Второе пополнение
        operation2 = {'operation_type': 'DEPOSIT', 'amount': '200.00'}
        response2 = client.post(self.operation_url, operation2, format="json")
        self.assertEqual(response2.status_code, 200)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.amount, Decimal('1300.00'))
