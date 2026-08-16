# utils/validators.py
from datetime import datetime

def validate_date(date_str: str) -> bool:
    """Проверяет формат даты ГГГГ-ММ-ДД"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def validate_chat_id(chat_id_str: str) -> bool:
    """Проверяет, что передан ID чата (целое число)"""
    try:
        int(chat_id_str)
        return True
    except ValueError:
        return False