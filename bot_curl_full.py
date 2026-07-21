import subprocess
import json
import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import db_simple

# Файл для хранения последнего обработанного update_id
LAST_ID_FILE = 'last_update_id.txt'

def get_last_update_id():
    try:
        with open(LAST_ID_FILE, 'r') as f:
            return int(f.read().strip())
    except:
        return 0

def save_last_update_id(update_id):
    with open(LAST_ID_FILE, 'w') as f:
        f.write(str(update_id))

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print("❌ Токен не найден!")
    exit(1)

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

def curl_request(url, method='GET', data=None):
    cmd = ["curl", "-s", "-X", method, url]
    if data:
        for key, value in data.items():
            cmd.extend(["-d", f"{key}={value}"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except:
        return None

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates?timeout=5"
    if offset:
        url += f"&offset={offset}"
    data = curl_request(url)
    if data and data.get('ok'):
        return data.get('result', [])
    return []

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    data = {'chat_id': chat_id, 'text': text}
    return curl_request(url, method='POST', data=data) is not None

def main():
    print("🤖 Бот-сборщик запущен (полная версия)")
    print(f"✅ Токен: {TOKEN[:10]}...")

    # Если файла с last_update_id нет, получим последний ID из Telegram
    if not os.path.exists(LAST_ID_FILE):
        print("🔄 Первый запуск: пропускаем старые обновления...")
        # Получаем одно обновление, чтобы узнать последний update_id
        url = f"{BASE_URL}/getUpdates?limit=1"
        data = curl_request(url)
        if data and data.get('ok') and data['result']:
            last_id = data['result'][-1]['update_id']
            save_last_update_id(last_id)
            print(f"✅ Установлен last_update_id: {last_id}")
        else:
            # Если обновлений нет, сохраняем 0
            save_last_update_id(0)

    last_update_id = get_last_update_id()
    print(f"📌 Последний update_id: {last_update_id}")

    while True:
        try:
            updates = get_updates(offset=last_update_id + 1 if last_update_id else None)
            for update in updates:
                update_id = update.get('update_id')
                if update_id:
                    last_update_id = update_id
                    save_last_update_id(update_id)

                message = update.get('message')
                if not message:
                    continue

                chat_id = message['chat']['id']
                user_id = message['from']['id']
                username = message['from'].get('username', '')
                first_name = message['from'].get('first_name', '')
                last_name = message['from'].get('last_name', '')
                text = message.get('text', '')
                date = message.get('date', datetime.now().isoformat())

                db_simple.save_user(user_id, username, first_name, last_name)
                db_simple.save_message(
                    message.get('message_id'),
                    chat_id,
                    user_id,
                    text,
                    date
                )

                print(f"📩 [{first_name}] {text[:50]}")

                # --- Обработка команд ---
                if text == '/start':
                    send_message(chat_id, "👋 Бот-сборщик работает! Все сообщения сохраняются.")
                elif text == '/help':
                    send_message(chat_id, "📚 Доступные команды:\n/start - приветствие\n/help - помощь\n/stats - статистика (админ)\n/export - экспорт данных (админ)")
                elif text == '/stats':
                    if db_simple.is_admin(user_id):
                        total, chats = db_simple.get_stats()
                        send_message(chat_id, f"📊 Статистика:\nВсего сообщений: {total}\nЧатов: {chats}")
                    else:
                        send_message(chat_id, "❌ У вас нет прав администратора.")
                elif text == '/export':
                    if db_simple.is_admin(user_id):
                        rows = db_simple.export_messages(chat_id, days=7)
                        if rows:
                            csv = "Дата,Пользователь,Текст\n"
                            for row in rows:
                                csv += f"{row[1]},{row[2]},{row[0].replace(',',' ')}\n"
                            url = f"{BASE_URL}/sendDocument"
                            cmd = ["curl", "-s", "-X", "POST", url,
                                   "-F", f"chat_id={chat_id}",
                                   "-F", "document=@-;filename=export.csv"]
                            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            p.communicate(input=csv.encode('utf-8'))
                        else:
                            send_message(chat_id, "❌ Нет сообщений за последние 7 дней.")
                    else:
                        send_message(chat_id, "❌ У вас нет прав администратора.")
                else:
                    pass  # игнорируем обычные сообщения

            time.sleep(1)

        except KeyboardInterrupt:
            print("\n⏹️ Остановка")
            break
        except Exception as e:
            print(f"❌ Ошибка в цикле: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
