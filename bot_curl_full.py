import sys
print("🔴 0. Скрипт начал выполнение")

try:
    import subprocess
    import json
    import time
    import os
    from datetime import datetime
    print("🔴 1. Импорты стандартные OK")
except Exception as e:
    print(f"🔴 Ошибка импорта стандартных модулей: {e}")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    from pathlib import Path
    print("🔴 2. Импорт dotenv OK")
except Exception as e:
    print(f"🔴 Ошибка импорта dotenv: {e}")
    sys.exit(1)

try:
    # Загружаем .env
    env_path = Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=env_path)
    print(f"🔴 3. .env загружен, путь: {env_path}")
except Exception as e:
    print(f"🔴 Ошибка загрузки .env: {e}")
    sys.exit(1)

try:
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        print("❌ Токен не найден в .env!")
        sys.exit(1)
    print(f"🔴 4. Токен получен: {TOKEN[:10]}...")

    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL не найден в .env!")
        sys.exit(1)
    print(f"🔴 5. DATABASE_URL получен: {DATABASE_URL[:30]}...")
except Exception as e:
    print(f"🔴 Ошибка чтения переменных: {e}")
    sys.exit(1)

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"
LAST_ID_FILE = 'last_update_id.txt'

try:
    import db_simple
    print("🔴 6. db_simple импортирован успешно")
except Exception as e:
    print(f"🔴 Ошибка импорта db_simple: {e}")
    sys.exit(1)

# --- Функции ---
def curl_request(url, method='GET', data=None):
    cmd = ["curl", "-s", "-X", method, url]
    if data:
        for key, value in data.items():
            cmd.extend(["-d", f"{key}={value}"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except Exception as e:
        print(f"❌ curl_request ошибка: {e}")
        return None

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates?timeout=5"
    if offset is not None:
        url += f"&offset={offset}"
    data = curl_request(url)
    if data and data.get('ok'):
        return data.get('result', [])
    return []

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    data = {'chat_id': chat_id, 'text': text}
    return curl_request(url, method='POST', data=data) is not None

def get_last_update_id():
    try:
        with open(LAST_ID_FILE, 'r') as f:
            return int(f.read().strip())
    except:
        return 0

def save_last_update_id(update_id):
    with open(LAST_ID_FILE, 'w') as f:
        f.write(str(update_id))

# --- main ---
def main():
    print("🔴 7. Вход в main()")
    try:
        # Удаляем вебхук
        delete_url = f"{BASE_URL}/deleteWebhook"
        curl_request(delete_url, method='GET')
        print("✅ Вебхук удалён (если был)")
    except Exception as e:
        print(f"❌ Ошибка удаления вебхука: {e}")

    print("🤖 Бот-сборщик запущен (полная версия)")

    if not os.path.exists(LAST_ID_FILE):
        print("🔄 Первый запуск: пропускаем старые обновления...")
        old_updates = get_updates(offset=None)
        if old_updates:
            last_id = old_updates[-1]['update_id']
            save_last_update_id(last_id)
            print(f"✅ Установлен last_update_id: {last_id}")
        else:
            save_last_update_id(0)
            print("✅ Нет старых обновлений, last_update_id = 0")

    last_update_id = get_last_update_id()
    print(f"📌 Текущий last_update_id: {last_update_id}")

    while True:
        try:
            offset = last_update_id + 1
            updates = get_updates(offset=offset)
            if updates:
                print(f"📦 Получено {len(updates)} обновлений")

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

                # Сохраняем в БД
                try:
                    db_simple.save_user(user_id, username, first_name, last_name)
                    db_simple.save_message(
                        message.get('message_id'),
                        chat_id,
                        user_id,
                        text,
                        date
                    )
                    chat_title = message['chat'].get('title', '')
                    chat_type = message['chat'].get('type', '')
                    db_simple.save_chat(chat_id, chat_title, chat_type)
                except Exception as db_error:
                    print(f"❌ Ошибка БД: {db_error}")

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
                        session = db_simple.get_session()
                        rows = session.query(db_simple.Message).filter(db_simple.Message.chat_id == chat_id).order_by(db_simple.Message.date).all()
                        session.close()
        
                        if rows:
                            csv_data = "Дата,Пользователь,Текст\n"
                            for row in rows:
                                # Получаем имя пользователя
                                user = session.query(db_simple.User).filter_by(telegram_id=row.user_id).first()
                                username = user.first_name if user else str(row.user_id)
                                csv_data += f"{row.date},{username},{row.text.replace(',',' ')}\n"
            
                            # Отправка через requests
                            url = f"{BASE_URL}/sendDocument"
                            files = {'document': ('export.csv', csv_data.encode('utf-8'))}
                            data = {'chat_id': chat_id}
                            try:
                                import requests
                                response = requests.post(url, data=data, files=files, timeout=30, verify=False)
                                if response.status_code == 200:
                                    send_message(chat_id, "✅ Файл отправлен!")
                                else:
                                    send_message(chat_id, f"❌ Ошибка: {response.status_code}")
                            except Exception as e:
                                send_message(chat_id, f"❌ Ошибка: {e}")
                        else:
                            send_message(chat_id, "❌ Нет сообщений в этом чате.")
                    else:
                        send_message(chat_id, "❌ У вас нет прав администратора.")

            time.sleep(1)

        except KeyboardInterrupt:
            print("\n⏹️ Остановка")
            break
        except Exception as e:
            print(f"❌ Ошибка в цикле: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Критическая ошибка в main: {e}")
        import traceback
        traceback.print_exc()