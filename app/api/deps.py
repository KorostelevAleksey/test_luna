from fastapi import Header, HTTPException, status

from app.config import settings


# Проверка заголовка ключа на эндпоинтах
async def verify_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
