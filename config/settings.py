import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

class Settings:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///telegram_aggregator.db')
    
    # Настройки сбора
    COLLECTOR_ENABLED = True
    COLLECT_REACTIONS = True
    COLLECT_MEDIA = True
    
    # Пути
    DATA_DIR = 'data'
    EXPORT_DIR = 'exports'
    MEDIA_DIR = 'media'

# Создаем экземпляр настроек для удобства
settings = Settings()
