import subprocess
import json
import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import db_simple

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print("❌ Токен не найден!")
    exit(1)

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# Инициализируем БД
db_simple.init_db()

def curl_request(url, method='GET', data=None):
    cmd = ["curl", "-s", "-X", method, url]
    if data:
        for key, value in data.items():
            cmd.extend(["-d", f"{key}={value}"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"❌ curl ошибка: {result.stderr}")
            return None
        return json.loads(result.stdout)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates?timeout=30"
    if offset:
        url += f"&offset={offset}"
    data = curl_request(url)
    if data and data.get('ok'):
        return data.get('result', [])
    return []

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    data = {'chat_id': chat_id, 'text': text}
    result = curl_request(url, method='POST', data=data)
    return result and result.get('ok', False)

def send_file(chat_id, file_path, caption=''):
    url = f"{BASE_URL}/sendDocument"
    # Для файла используем multipart/form-data через curl
    cmd = ["curl", "-s", "-X", "POST", url, "-F", f"chat_id={chat_id}", "-F", f"document=@{file_path}", "-F", f"caption={caption}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"❌ curl ошибка: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def export_messages(chat_id, start_date, end_date, user_id):
    rows = db_simple.get_messages_by_chat_and_date(chat_id, start_date, end_date)
    if not rows:
        send_message(user_id, "❌ Нет сообщений за выбранный период.")
        return
    # Создаём CSV
    filename = f"export_{chat_id}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    import csv
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Дата', 'Пользователь', 'Текст', 'Тип медиа'])
        for row in rows:
            writer.writerow([row['created_at'], f"{row['first_name']} {row['last_name'] or ''}", row['text'], row['media_type']])
    send_file(user_id, filename, f"📊 Экспорт чата за {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
    os.remove(filename)

def main():
    print("🤖 Бот-сборщик запущен (полная версия)")
    print(f"✅ Токен: {TOKEN[:10]}...")
    last_update_id = 0
    
    while True:
        try:
            updates = get_updates(offset=last_update_id + 1 if last_update_id else None)
            
            for update in updates:
                update_id = update.get('update_id')
                if update_id:
                    last_update_id = update_id
                
                message = update.get('message')
                if not message:
                    continue
                
                chat_id = message['chat']['id']
                user_id = message['from']['id']
                username = message['from'].get('first_name', 'Пользователь')
                text = message.get('text', '')
                chat_name = message['chat'].get('title', message['chat'].get('first_name', 'private'))
                chat_type = message['chat'].get('type', 'private')
                
                # Сохраняем пользователя и чат
                db_simple.save_user(user_id, message['from'].get('username'), message['from'].get('first_name'), message['from'].get('last_name'))
                db_simple.save_chat(chat_id, chat_name, chat_type)
                
                # Сохраняем сообщение
                db_simple.save_message(message['message_id'], chat_id, user_id, text)
                
                print(f"📩 [{username}] {text}")
                
                # Обработка команд
                if text == '/start':
                    send_message(chat_id, "✅ Бот-сборщик работает! Все сообщения сохраняются.")
                elif text == '/help':
                    send_message(chat_id, "📚 Доступные команды:\n/start - приветствие\n/help - помощь\n/stats - статистика (админ)\n/export - экспорт данных (админ)")
                elif text == '/stats':
                    if db_simple.is_admin(user_id):
                        chats = db_simple.get_all_chats()
                        stats = "📊 Статистика по чатам:\n"
                        for chat in chats:
                            # Получаем количество сообщений
                            conn = db_simple.get_connection()
                            cur = conn.cursor()
                            cur.execute('SELECT COUNT(*) FROM messages WHERE chat_id = ?', (chat['chat_id'],))
                            count = cur.fetchone()[0]
                            conn.close()
                            stats += f"{chat['chat_name']}: {count} сообщений\n"
                        send_message(chat_id, stats)
                    else:
                        send_message(chat_id, "❌ У вас нет прав администратора.")
                elif text == '/export':
                    if db_simple.is_admin(user_id):
                        send_message(chat_id, "📤 Экспорт за последние 7 дней...")
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=7)
                        export_messages(chat_id, start_date, end_date, user_id)
                    else:
                        send_message(chat_id, "❌ У вас нет прав администратора.")
                else:
                    # Не отвечаем на обычные сообщения, только сохраняем
                    pass
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\n⏹️ Остановка")
            break
        except Exception as e:
            print(f"❌ Ошибка в цикле: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
