import subprocess
import json
import time

TOKEN = '8941109488:AAFGNfx8U3s1DGMV2as4rORT2LTWumdassA'
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

def curl_request(url, method='GET', data=None):
    cmd = ["curl", "-s", "-X", method, url]
    if data:
        for k, v in data.items():
            cmd.extend(["-d", f"{k}={v}"])
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(res.stdout)
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

last_id = 0
print("✅ Echo-бот запущен. Ждём сообщения...")
while True:
    updates = get_updates(offset=last_id + 1)
    for u in updates:
        last_id = u['update_id']
        msg = u.get('message')
        if msg and 'text' in msg:
            chat_id = msg['chat']['id']
            text = msg['text']
            print(f"📩 Получено: {text}")
            send_message(chat_id, f"📝 Вы написали: {text}")
    time.sleep(1)
