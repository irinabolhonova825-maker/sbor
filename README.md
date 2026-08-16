# Telegram Aggregator Bot
Бот для сбора сообщений из чатов Telegram, сохранения вложений и экспорта данных в CSV.

## Возможности
1. 📥 Сохраняет все текстовые сообщения, фото, документы и другие файлы из чатов, в которые добавлен бот.

2. 📤 Экспорт сообщений за произвольный период в формате CSV.

3. 📊 Статистика: общее количество сообщений, чатов, уникальных пользователей (доступна только администраторам).

4. 💾 Сохранение скачанных файлов в локальную папку media/ с привязкой к записи сообщения в БД.

5. 🛢 Использует PostgreSQL для надёжного хранения данных.

## Команды бота
Команда	Описание
/start	Приветственное сообщение
/help	Список доступных команд
/export YYYY-MM-DD YYYY-MM-DD [chat_id]	Экспорт сообщений за указанный период. Если передан chat_id — экспорт только из этого чата (опционально).
/stats / /status	Статистика по чатам и сообщениям (только для администраторов)

## Установка и запуск
Требования
Python 3.8 или выше
PostgreSQL 12+
Telegram Bot Token (получить у @BotFather)

Шаги
1. Клонируйте репозиторий
git clone https://github.com/irinabolhonova825-maker/sbor.git
cd sbor
2. Создайте и активируйте виртуальное окружение
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows
3. Установите зависимости
pip install -r requirements.txt
4. Настройте переменные окружения
Скопируйте файл .env.example в .env и заполните его своими данными:
cp .env.example .env
Пример содержимого .env:
env
BOT_TOKEN=ваш_токен_бота
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
ADMIN_IDS=123456789,987654321
LOG_LEVEL=INFO
MEDIA_DIR=media
ADMIN_IDS — список числовых Telegram ID администраторов через запятую.

5. Создайте базу данных PostgreSQL
Выполните в psql или через ваш любимый клиент:
CREATE DATABASE dbname;
CREATE USER user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE dbname TO user;
6. Убедитесь, что строка DATABASE_URL соответствует созданным учётным данным.

7. Запустите бота
python3 main.py
При успешном запуске в консоли появится сообщение: Бот запущен.

## Структура проекта
telegram-aggregator/
├── main.py                 # Главный файл бота
├── db_simple.py            # Модели и подключение к БД
├── utils/
│   ├── __init__.py
│   ├── logger.py           # Настройка логирования
│   └── validators.py       # Вспомогательные функции
├── media/                  # Папка для скачанных файлов (создаётся автоматически)
├── .env.example            # Пример переменных окружения
├── .gitignore
├── requirements.txt
└── README.md
