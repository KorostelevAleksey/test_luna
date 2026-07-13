# Payment Service

Асинхронный сервис приёма платежей на FastAPI. API принимает платёж и сразу отвечает `202 Accepted`, дальнейшая обработка выполняется в фоне через RabbitMQ.

## Стек

- **Python 3.13**, **FastAPI**, **SQLAlchemy** (async), **Alembic**
- **PostgreSQL** — хранение платежей и outbox
- **RabbitMQ** + **FastStream** — очередь событий
- **Docker Compose** — локальный запуск

## Архитектура

```
POST /api/v1/payments
        │
        ├─ PostgreSQL: payments (status=pending)
        ├─ PostgreSQL: outbox (та же транзакция)
        └─ 202 Accepted
                │
        Outbox publisher (в API)
                │
        RabbitMQ: payments.new
                │
        Consumer
                ├─ sleep 2–5 сек (эмуляция шлюза)
                ├─ succeeded / failed → обновление в БД
                └─ POST webhook_url клиента
```

При ошибках обработки сообщение уходит в **DLQ** (`payments.new.dlq`) после исчерпания попыток доставки.

## Быстрый старт

```bash
docker compose up --build
```

Сервисы:

| Сервис   | URL / порт              |
|----------|-------------------------|
| API      | http://localhost:8000   |
| Swagger  | http://localhost:8000/docs |
| RabbitMQ | http://localhost:15672 (guest/guest) |
| Postgres | localhost:5432          |

При старте API автоматически выполняется `alembic upgrade head`.

## Аутентификация

Все эндпоинты `/api/v1/payments` требуют заголовок:

```
X-API-Key: test-key
```

Значение по умолчанию задаётся в `app/config.py` (`api_key`). Можно переопределить через переменную окружения `API_KEY` или файл `.env`.

## API

### Создание платежа

```http
POST /api/v1/payments
Content-Type: application/json
X-API-Key: test-key
Idempotency-Key: unique-key-123

{
  "amount": "100.50",
  "currency": "RUB",
  "description": "Тестовый платёж",
  "meta": {"order_id": "42"},
  "webhook_url": "https://example.com/webhook"
}
```

**Ответ `202 Accepted`:**

```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2026-07-13T12:00:00+03:00"
}
```

Повторный запрос с тем же `Idempotency-Key` вернёт тот же платёж без создания дубликата.

### Получение платежа

```http
GET /api/v1/payments/{payment_id}
X-API-Key: test-key
```

**Ответ `200 OK`:**

```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "amount": "100.50",
  "currency": "RUB",
  "description": "Тестовый платёж",
  "meta": {"order_id": "42"},
  "status": "succeeded",
  "idempotency_key": "unique-key-123",
  "webhook_url": "https://example.com/webhook",
  "created_at": "2026-07-13T12:00:00+03:00",
  "processed_at": "2026-07-13T12:00:03+03:00"
}
```

### Webhook клиенту

После обработки consumer отправляет `POST` на `webhook_url`:

```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "succeeded",
  "amount": "100.50",
  "currency": "RUB",
  "processed_at": "2026-07-13T12:00:03+03:00"
}
```

## Переменные окружения

| Переменная             | По умолчанию                                              | Описание                    |
|------------------------|-----------------------------------------------------------|-----------------------------|
| `DATABASE_URL`         | `postgresql+asyncpg://postgres:postgres@localhost:5432/luna-payments` | URL PostgreSQL      |
| `RABBITMQ_URL`         | `amqp://guest:guest@localhost:5672/`                      | URL RabbitMQ                |
| `API_KEY`              | `test-key`                                                | Ключ для `X-API-Key`        |
| `OUTBOX_POLL_INTERVAL` | `1.0`                                                     | Интервал опроса outbox (сек)|
| `CONSUMER_MAX_RETRIES` | `3`                                                       | Лимит повторов в очереди    |

## Структура проекта

```
app/
  api/v1/payments.py   # HTTP-эндпоинты
  api/deps.py          # проверка X-API-Key
  models/              # SQLAlchemy-модели
  schemas/             # Pydantic-схемы
  services/
    outbox_publisher.py  # публикация outbox → RabbitMQ
    consumer.py          # обработка платежей и webhook
    queues.py            # конфигурация очередей и DLQ
alembic/               # миграции БД
```

