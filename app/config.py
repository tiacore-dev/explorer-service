import os
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()


class Settings:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ASSISTANT_ID = os.getenv('ASSISTANT_ID')
    PORT = os.getenv('PORT')
    API_KEY = os.getenv('API_KEY')
