import sqlite3
from datetime import datetime, timedelta

DB_NAME = 'telegram_aggregator.db'

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            chat_id INTEGER,
            user_id INTEGER,
            text TEXT,
            date TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            chat_name TEXT,
            chat_type TEXT
        )
    ''')
    conn.commit()
    return conn

def init_db():
    conn = get_connection()
    conn.close()

def save_user(telegram_id, username, first_name, last_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO users (telegram_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
    ''', (telegram_id, username, first_name, last_name))
    conn.commit()
    conn.close()

def save_message(message_id, chat_id, user_id, text, date=None):
    if date is None:
        date = datetime.now().isoformat()
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO messages (message_id, chat_id, user_id, text, date)
        VALUES (?, ?, ?, ?, ?)
    ''', (message_id, chat_id, user_id, text, date))
    conn.commit()
    conn.close()

def save_chat(chat_id, chat_name, chat_type):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO chats (chat_id, chat_name, chat_type)
        VALUES (?, ?, ?)
    ''', (chat_id, chat_name, chat_type))
    conn.commit()
    conn.close()

def is_admin(telegram_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT is_admin FROM users WHERE telegram_id = ?', (telegram_id,))
    row = c.fetchone()
    conn.close()
    return row and row[0] == 1

def get_stats():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM messages')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT chat_id) FROM messages')
    chats = c.fetchone()[0]
    conn.close()
    return total, chats

def export_messages(chat_id, days=7):
    conn = get_connection()
    c = conn.cursor()
    since = (datetime.now() - timedelta(days=days)).isoformat()
    c.execute('''
        SELECT text, date, user_id FROM messages
        WHERE chat_id = ? AND date >= ?
        ORDER BY date
    ''', (chat_id, since))
    rows = c.fetchall()
    conn.close()
    return rows
