import os
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()
print("RABBIT_URL:", os.getenv("RABBITMQ_USER"), os.getenv("RABBITMQ_PASS"))


class Settings:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ASSISTANT_ID = os.getenv('ASSISTANT_ID')
    PORT = os.getenv('PORT')
    API_KEY = os.getenv('API_KEY')
    RABBIT_USER = os.getenv("RABBITMQ_USER", "user")
    RABBIT_PASS = os.getenv("RABBITMQ_PASS", "pass")
    RABBIT_HOST = os.getenv("RABBITMQ_HOST", "localhost")
    QUEUE_NAME = "site_analysis_tasks"
