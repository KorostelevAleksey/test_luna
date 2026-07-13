from contextlib import asynccontextmanager

import fastapi
import fastapi_swagger_dark as fsd

from app.api.v1.payments import router as payments_router
from app.db.session import engine
from app.services.outbox_publisher import start_outbox_publisher, stop_outbox_publisher


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    # При старте API — фоновый outbox publisher в RabbitMQ
    broker, task, stop_event = await start_outbox_publisher()
    yield
    # останавливаем publisher по ивенту
    await stop_outbox_publisher(broker, task, stop_event)
    await engine.dispose()


app = fastapi.FastAPI(docs_url=None, lifespan=lifespan)
router = fastapi.APIRouter()

# Темная тема для свагера
fsd.install(router)
app.include_router(router)
app.include_router(payments_router, prefix="/api/v1")
