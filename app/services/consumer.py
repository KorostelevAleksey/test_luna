import asyncio
import logging
import random
from datetime import datetime
from pathlib import Path
from uuid import UUID

import httpx
from faststream import FastStream
from faststream.middlewares import AckPolicy
from faststream.rabbit import RabbitBroker
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from app.config import MSK, settings
from app.db.session import async_session
from app.models.payments import Payment
from app.services.queues import payments_dlq, payments_dlx, payments_queue

LOG_FILE = Path(settings.consumer_log_path)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

broker = RabbitBroker(settings.rabbitmq_url)
app = FastStream(broker)


@retry(stop=stop_after_attempt(1), wait=wait_exponential(multiplier=1, min=4, max=10))
async def send_webhook(payment: Payment) -> None:
    # POST на webhook_url клиента с результатом платежа
    body = {
        "payment_id": str(payment.payment_id),
        "status": payment.status,
        "amount": str(payment.amount),
        "currency": payment.currency,
        "processed_at": payment.processed_at.isoformat(),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(payment.webhook_url, json=body)
        response.raise_for_status()
    logger.info("webhook sent for payment %s", payment.payment_id)


@broker.subscriber(payments_queue, ack_policy=AckPolicy.NACK_ON_ERROR)
async def handle_payment(payload: dict) -> None:
    payment_id = UUID(payload["payment_id"])
    logger.info("processing payment %s", payment_id)
    # raise RuntimeError("test dlq")

    # Эмуляция задержки 2–5 сек
    await asyncio.sleep(random.uniform(2, 5))

    # 90% на успех
    # TODO вынести в конфиг
    status = "succeeded" if random.random() < 0.9 else "failed"
    processed_at = datetime.now(MSK)

    async with async_session() as session:
        payment = await session.get(Payment, payment_id)
        # Проверка на обработанный платеж
        if payment.status != "pending":
            logger.info("payment %s already processed: %s", payment_id, payment.status)
            return
        payment.status = status
        payment.processed_at = processed_at
        await session.commit()

    logger.info("payment %s processed: %s", payment_id, status)
    # Отправка webhook
    try:
        await send_webhook(payment)
    except RetryError as exc:
        logger.error("webhook failed for payment %s: %s", payment.payment_id, exc)


@broker.subscriber(payments_dlq, exchange=payments_dlx)
async def handle_dead_letter(payload: dict) -> None:
    # Сообщение исчерпало retry и попало в DLQ
    logger.error("message in DLQ: %s", payload)


if __name__ == "__main__":
    asyncio.run(app.run())
