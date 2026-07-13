from faststream.rabbit import RabbitExchange, RabbitQueue
from faststream.rabbit.schemas import ExchangeType, QueueType

from app.config import settings

payments_dlx = RabbitExchange(settings.payments_dlx, type=ExchangeType.DIRECT)
payments_dlq = RabbitQueue(settings.payments_dlq)
payments_queue = RabbitQueue(
    settings.payments_queue,
    queue_type=QueueType.QUORUM,
    arguments={
        "x-dead-letter-exchange": settings.payments_dlx,
        "x-dead-letter-routing-key": settings.payments_dlq,
        "x-delivery-limit": settings.consumer_max_retries,
    },
)
