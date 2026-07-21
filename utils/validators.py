from datetime import datetime
import re

def validate_date(date_string):
    """Проверка формата даты"""
    try:
        datetime.strptime(date_string, '%d-%m-%Y')
        return True
    except ValueError:
        return False

def validate_chat_id(chat_id):
    """Проверка ID чата"""
    try:
        chat_id = int(chat_id)
        return chat_id < 0
    except ValueError:
        return False

def validate_telegram_id(telegram_id):
    """Проверка Telegram ID"""
    try:
        telegram_id = int(telegram_id)
        return telegram_id > 0
    except ValueError:
        return False

def sanitize_text(text):
    """Очистка текста от опасных символов"""
    if not text:
        return ""
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text.strip()
