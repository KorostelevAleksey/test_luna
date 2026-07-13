import asyncio
from datetime import datetime

from faststream.rabbit import RabbitBroker
from sqlalchemy import select

from app.config import MSK, settings
from app.db.session import async_session
from app.models.outbox import Outbox
from app.services.queues import payments_queue


async def _publish_pending(broker: RabbitBroker) -> None:
    # Берем id неопубликованных записей
    async with async_session() as session:
        outbox_ids = (
            await session.scalars(
                select(Outbox.outbox_id).where(Outbox.published_at.is_(None)).limit(10)
            )
        ).all()

    # Каждую запись публикуем в отдельной сессии
    for outbox_id in outbox_ids:
        async with async_session() as session:
            outbox = await session.get(Outbox, outbox_id)
            if outbox is None or outbox.published_at is not None:
                continue
            await broker.publish(outbox.payload, queue=payments_queue)
            outbox.published_at = datetime.now(MSK)
            await session.commit()


async def outbox_publisher_loop(broker: RabbitBroker, stop_event: asyncio.Event) -> None:
    # читаем outbox по poll и шлем в RabbitMQ
    while not stop_event.is_set():
        await _publish_pending(broker)
        try:
            # ждем ивента или таймаута в wait_for, а не делаем sleep, так как если outbox_poll_interval будет большой, 
            # придется ждать это время при остановке приложения для корректного завершения
            await asyncio.wait_for(stop_event.wait(), timeout=settings.outbox_poll_interval)
        except TimeoutError:
            pass


async def start_outbox_publisher() -> tuple[RabbitBroker, asyncio.Task, asyncio.Event]:
    broker = RabbitBroker(settings.rabbitmq_url)
    await broker.start()
    stop_event = asyncio.Event() # создаем ивент для остановки
    task = asyncio.create_task(outbox_publisher_loop(broker, stop_event)) # создаем такс для выполнения цикла
    return broker, task, stop_event


async def stop_outbox_publisher(
    broker: RabbitBroker, task: asyncio.Task, stop_event: asyncio.Event
) -> None:
    stop_event.set()
    await task
    await broker.stop()
