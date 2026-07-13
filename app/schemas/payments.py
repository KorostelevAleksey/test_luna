from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Currency = Literal["RUB", "USD", "EUR"]
PaymentStatus = Literal["pending", "succeeded", "failed"]


# Тело post /payments
class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: Currency
    description: str | None = None
    meta: dict = Field(default_factory=dict)
    webhook_url: str


# Ответ post /payments
class PaymentCreateResponse(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    created_at: datetime


# Ответ get /payments
class PaymentData(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # мепинг из ORM payments

    payment_id: UUID
    amount: Decimal
    currency: Currency
    description: str | None
    meta: dict
    status: PaymentStatus
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None = None
