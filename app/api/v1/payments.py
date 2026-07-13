from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_api_key
from app.config import MSK, settings
from app.db.session import get_db
from app.models.outbox import Outbox
from app.models.payments import Payment
from app.schemas.payments import PaymentCreate, PaymentCreateResponse, PaymentData

# просим api-key
router = APIRouter(prefix="/payments", dependencies=[Depends(verify_api_key)])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=PaymentCreateResponse)
async def create_payment(
    body: PaymentCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_db),
) -> PaymentCreateResponse:
    """Создание платежа. Возвращает 202 Accepted — платеж принят к асинхронной обработке."""
    # Идемпотентность
    existing = await session.scalar(
        select(Payment).where(Payment.idempotency_key == idempotency_key)
    )
    if existing:
        return PaymentCreateResponse(
            payment_id=existing.payment_id,
            status=existing.status,
            created_at=existing.created_at,
        )

    created_at = datetime.now(MSK)
    payment = Payment(
        amount=body.amount,
        currency=body.currency,
        description=body.description,
        meta=body.meta,
        status="pending",
        idempotency_key=idempotency_key,
        webhook_url=body.webhook_url,
        created_at=created_at,
    )
    session.add(payment)
    await session.flush()  # получаем payment_id до комита

    # Outbox в той же транзакции
    outbox = Outbox(
        payment_id=payment.payment_id,
        event_type=settings.payments_queue,
        payload={"payment_id": str(payment.payment_id)},
        created_at=created_at,
    )
    session.add(outbox)
    await session.commit()
    await session.refresh(payment)

    return PaymentCreateResponse(
        payment_id=payment.payment_id,
        status=payment.status,
        created_at=payment.created_at,
    )


@router.get("/{payment_id}", response_model=PaymentData)
async def get_payment(
    payment_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> PaymentData:
    """Получение платежа по идентификатору."""
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return PaymentData.model_validate(payment)
