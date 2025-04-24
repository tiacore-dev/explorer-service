from fastapi import FastAPI
import openai
from app.logger import setup_logger
from app.routes import register_routes
from app.config import Settings


def create_app() -> FastAPI:
    app = FastAPI(title="Explorer")

    app.state.settings = Settings()
    openai.api_key = app.state.settings.OPENAI_API_KEY
   # Конфигурация Tortoise ORM

    setup_logger()
    # Регистрация маршрутов
    register_routes(app)

    return app
