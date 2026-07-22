# Telegram Aggregator — сборщик корпоративных переписок

Бот для автоматического сбора сообщений из корпоративных чатов Telegram. Сохраняет текст сообщений, авторов, даты и чаты в SQLite-базу данных. Поддерживает команды для администраторов: статистика и экспорт данных.

## Возможности

- Сохранение всех текстовых сообщений из личных чатов и групп.
- Автоматическое создание базы данных SQLite.
- Разграничение прав: обычные пользователи только читают приветствие, администраторы управляют ботом.
- Работает через `curl` (обход проблем с SSL/таймаутами в некоторых окружениях).

## Требования

- Python 3.8+
- Установленные пакеты: `python-dotenv`, `sqlalchemy` (и `psycopg2-binary` – если используется PostgreSQL)
- SQLite (встроенный) или PostgreSQL (опционально)

## Установка

1. Клонируйте репозиторий:
git clone https://github.com/irinabolhonova825-maker/sbor.git
cd sbor

2. Установите зависимости:
pip install python-dotenv

3. Получите токен бота
Откройте Telegram, найдите @BotFather.
Отправьте команду /newbot и следуйте инструкциям (выберите имя и username).
Скопируйте полученный токен (например, 123456:ABC-DEF...).

4. Настройте окружение
Создайте файл .env в корне проекта
| Переменная | Описание | Пример |
|------------|----------|--------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather | `123456:ABC-DEF...` |
| `DATABASE_URL` | Строка подключения к PostgreSQL | `postgresql://user:password@localhost/telegram_aggregator` |

5. Добавьте себя как администратора

Выполните команду (замените 123456789 на ваш Telegram ID, его можно узнать у бота @userinfobot):
python3 add_admin.py

Если скрипт отсутствует, создайте его или выполните команду:
python3 -c "
from db_simple import User, SessionLocal
session = SessionLocal()
user = session.query(User).filter_by(telegram_id=1266582465).first()
if not user:
    user = User(telegram_id=1266582465, username='admin', first_name='Admin', is_admin=1)
    session.add(user)
else:
    user.is_admin = 1
session.commit()
session.close()
print('Администратор добавлен')
"
6. Запустите бота
python3 bot_curl_full.py

Бот начнёт опрашивать Telegram API и отвечать на команды.

Команды бота
Команда	Описание
/start	Приветствие и краткая справка
/help	Список доступных команд
/stats	(только админ) Показывает общее количество сообщений и чатов
/export	(только админ) Отправляет CSV-файл с сообщениями за последние 7 дней

.
├── bot_curl_full.py       # основной скрипт бота
├── db_simple.py           # модели и работа с БД (SQLAlchemy)
├── add_admin.py           # скрипт для добавления администратора
├── requirements.txt       # зависимости
├── .env                   # переменные окружения (токен, БД)
├── .gitignore             # исключения для Git
├── README.md              # этот файл
└── telegram_aggregator.db # SQLite-база (создаётся автоматически)

 Переключение между SQLite и PostgreSQL
По умолчанию бот использует SQLite (файл telegram_aggregator.db).
Чтобы переключиться на PostgreSQL:
Установите psycopg2-binary: pip install psycopg2-binary.

В файле .env измените DATABASE_URL на:
DATABASE_URL=postgresql://user:password@host:port/database

Убедитесь, что PostgreSQL запущен и база данных существует.

Перезапустите бота – таблицы создадутся автоматически.