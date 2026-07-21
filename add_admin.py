import sqlite3

# Подключаемся к базе данных
conn = sqlite3.connect('telegram_aggregator.db')
cursor = conn.cursor()

# Создаём таблицу пользователей, если её нет
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    is_admin INTEGER DEFAULT 0
)
''')

# Добавляем администратора (замените 1266582465 на ваш ID)
telegram_id = 1266582465
cursor.execute('''
INSERT OR REPLACE INTO users (telegram_id, username, first_name, is_admin)
VALUES (?, 'admin', 'Admin', 1)
''', (telegram_id,))

conn.commit()
conn.close()

print(f"✅ Пользователь {telegram_id} добавлен как администратор!")
