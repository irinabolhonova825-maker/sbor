import logging
import sys
from datetime import datetime

def setup_logger(name=None, level=logging.INFO):
    """Настройка логгера"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    import os
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Добавляем обработчик для записи в файл
    file_handler = logging.FileHandler(f'logs/app_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger
