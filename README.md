# Wallet REST API
Django REST API для управления электронными кошельками с поддержкой конкурентных операций и полной контейнеризацией.

## 🚀 Основные возможности
✅ Создание кошельков с UUID идентификаторами

✅ Пополнение баланса (DEPOSIT операции)

✅ Снятие средств (WITHDRAW операции)

✅ Просмотр текущего баланса

✅ Защита от race condition при параллельных операциях

✅ Полная Docker-контейнеризация

✅ Автоматическое тестирование конкурентности

## 🛠 Технологический стек

### Backend: 
<li> Django 4.2 + Django REST Framework </li>

### Database: 
<li> PostgreSQL 15 </li>

### Контейнеризация: 
<li> Docker + Docker Compose </li>

### Язык: 
<li> Python 3.12 </li>

## Тестирование: Django Test Framework + конкурентные тесты

## 📋 Требования
Docker 20.10+

Docker Compose 2.0+

⚡ Быстрый старт
Запуск с Docker Compose
bash
##  Клонирование репозитория (если нужно)
`git clone <repository-url>
cd Tproject_wallet`

## Создание файла окружения
`cp .env.example .env`

## Запуск проекта
`docker-compose up --build`

Проект будет доступен по http://localhost:8000
## Ручная установка (без Docker)

bash

Установка зависимостей

`pip install -r requirements.txt`

## Настройка базы данных
`python manage.py migrate`

## Запуск сервера
`python manage.py runserver`
📁 Структура проекта
text
Tproject_wallet/
├── config/                 # Настройки Django проекта
├── wallet/                 # Приложение кошельков
│   ├── models.py          # Модель Wallet
│   ├── views.py           # API представления
│   ├── serializers.py     # DRF сериализаторы
│   ├── tests.py           # Тесты (включая конкурентные)
│   └── urls.py            # Маршруты API
├── docker-compose.yml     # Docker Compose конфигурация
├── Dockerfile             # Образ приложения
├── requirements.txt       # Python зависимости
└── manage.py             # Django management script

## 🔌 API Endpoints
Получить информацию о кошельке
`http
GET /api/v1/wallets/{wallet_uuid}`
```Response:
json
{
  "id": "uuid-кошелька",
  "amount": "1000.00",
  "at_create": "2024-01-15T10:30:00Z",
  "time_update": "2024-01-15T10:35:00Z"
}
```

Выполнить операцию с кошельком
`http
POST /api/v1/wallets/{wallet_uuid}/operation`

Request Body:
```
json
{
  "operation_type": "DEPOSIT",  // или "WITHDRAW"
  "amount": "1000.00"
}
```
Response:
```
json
{
  "message": "Кошелек пополнен",
  "wallet": {
    "id": "uuid-кошелька",
    "amount": "2000.00",
    "at_create": "2024-01-15T10:30:00Z",
    "time_update": "2024-01-15T10:35:00Z"
  }
}
```
## 🧪 Тестирование
Запуск всех тестов

bash 

`python manage.py test --keepdb wallet
`

Что тестируется:

<ol> Множественные одновременные пополнения

Параллельные снятия средств

Защита от race condition

Смешанные операции (пополнения + снятия)

Поведение блокировок БД </ol>

## 🔒 Конкурентная безопасность
Система обеспечивает корректную работу при параллельных запросах благодаря:

<ol> Пессимистические блокировки python </ol>

 Блокировка кошелька для изменения

`wallet = Wallet.objects.select_for_update().get(id=wallet_uuid)`

Атомарные операции python

Атомарное обновление баланса

` Wallet.objects.filter(id=wallet_uuid).update(amount=models.F('amount') + amount) `

## 🐳 Docker команды
bash
Запуск в фоновом режиме

`docker-compose up -d`

## Просмотр логов
````
docker-compose logs -f web
docker-compose logs -f db
````

## Выполнение команд в контейнере
```
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py shell
```

## Остановка контейнеров
`docker-compose down`

## Полная очистка (включая volumes)
`docker-compose down -v`

## 📊 Примеры использования
Создание кошелька через Django Admin
bash

`docker-compose exec web python manage.py createsuperuser`

Затем зайдите в http://localhost:8000/admin


## Тестирование API через curl

Получить баланс

bash 

`curl http://localhost:8000/api/v1/wallets/{wallet_uuid}`

# Пополнить кошелек
```
curl -X POST http://localhost:8000/api/v1/wallets/{wallet_uuid}/operation \
  -H "Content-Type: application/json" \
  -d '{"operation_type": "DEPOSIT", "amount": "1000.00"}'
  ```

# Снять средства
```
curl -X POST http://localhost:8000/api/v1/wallets/{wallet_uuid}/operation \
  -H "Content-Type: application/json" \
  -d '{"operation_type": "WITHDRAW", "amount": "500.00"}'
 ```
## 🚨 Обработка ошибок

API возвращает соответствующие HTTP статусы:

200 OK - операция успешна

400 Bad Request - невалидные данные

404 Not Found - кошелек не найден

500 Internal Server Error - внутренняя ошибка сервера 


## 🔧 Настройка окружения
Создайте файл .env на основе .env.example:
```
env
SECRET_KEY =
DEBUG =

# Postgresql
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_HOST=
POSTGRES_PORT=
```
## 📄 Лицензия