from fastapi import HTTPException, Header
from app.config import Settings


settings = Settings()


async def check_api_key(x_api_key: str = Header(...)):
    if x_api_key == settings.API_KEY:
        return "ok"
    else:
        raise HTTPException(status_code=401, detail="Неверный апи ключ")
