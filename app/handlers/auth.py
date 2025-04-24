from fastapi import HTTPException
from app.config import Settings


settings = Settings()


async def check_api_key(api_key: str):
    if api_key == settings.API_KEY:
        return "ok"
    else:
        raise HTTPException(status_code=401, detail="Неверный апи ключ")
