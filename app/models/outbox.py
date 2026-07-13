from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Outbox(Base):
    __tablename__ = "outbox"

    outbox_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    payment_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    event_type: Mapped[str] = mapped_column(String(255))  # имя очереди
    payload: Mapped[dict] = mapped_column(JSONB)  # тело сообщения для RabbitMQ
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
