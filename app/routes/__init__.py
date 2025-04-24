from .explore_route import explore_router
# Функция для регистрации всех маршрутов


def register_routes(app):
    app.include_router(explore_router, prefix="/api", tags=["Explore"])
