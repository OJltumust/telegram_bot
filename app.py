from flask import Flask, request
import requests
import json
import openpyxl
from io import BytesIO
import dropbox
import base64
import requests
import json

app = Flask(__name__)

# Telegram config
BOT_TOKEN = "7294714166:AAFK1WNxkPJoUVzMpL5jiJ98ApvVPGvlbzk"
ADMIN_CHAT_ID = "731634508"
WEBHOOK_URL = "https://telegram-bot-flsb.onrender.com/webhook"  # установить при запуске

# Dropbox config
DROPBOX_REFRESH_TOKEN = "sjcdNshPfKEAAAAAAAAAAdXjVoN5r2jLr2k2z7HRfFQLrUBgMiQYMY1XUX8vqnMG"
DROPBOX_CLIENT_ID = "m7hgidj0oux4sbi"
DROPBOX_CLIENT_SECRET = "gnxkj5zh1b0mvfu"
APP_FOLDER = "/BeautyBar"


def refresh_access_token():
    url = "https://api.dropboxapi.com/oauth2/token"
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{DROPBOX_CLIENT_ID}:{DROPBOX_CLIENT_SECRET}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": DROPBOX_REFRESH_TOKEN,
    }

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        token = response.json().get("access_token")
        return token
    else:
        print("❌ Failed to refresh Dropbox token:")
        print("Status code:", response.status_code)
        print("Response:", response.text)
        return None

def get_dropbox_client():
    from dropbox import Dropbox
    token = refresh_access_token()
    if token:
        return Dropbox(token)
    else:
        raise Exception("❌ access_token is None — проверь refresh_token, client_id или secret.")
def update_balance(phone, amount):
    dbx = get_dropbox_client()
    path = f"{APP_FOLDER}/{phone}/{phone}_appointments.xlsx"

    # 1. Скачиваем Excel
    _, res = dbx.files_download(path)
    workbook = openpyxl.load_workbook(BytesIO(res.content))
    sheet = workbook.active

    # 2. Прочитать текущий баланс из ячейки E1 (например)
    current_balance_cell = sheet["E1"]
    try:
        current_balance = float(current_balance_cell.value)
    except (TypeError, ValueError):
        current_balance = 0.0

    # 3. Добавить сумму пополнения
    try:
        amount_float = float(amount)
    except ValueError:
        amount_float = 0.0

    new_balance = current_balance + amount_float

    # 4. Записать обновлённый баланс обратно в ячейку E1
    current_balance_cell.value = new_balance

    # 5. (Опционально) Добавить запись о пополнении в новую строку
    sheet.append([f"Пополнение от Telegram", phone, f"{amount} грн"])

    # 6. Сохраняем и загружаем обратно в Dropbox
    bio = BytesIO()
    workbook.save(bio)
    bio.seek(0)
    dbx.files_upload(bio.read(), path, mode=dropbox.files.WriteMode.overwrite)



@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.json
    print("🔔 Webhook received:", json.dumps(data, indent=2))

    if "callback_query" in data:
        try:
            query = data["callback_query"]
            print("🔘 Callback query:", query)
            print("📦 callback_data (raw):", query["data"])

            parts = query["data"].split("|")
            if len(parts) == 3 and parts[0] == "confirm":
                action, phone, amount = parts
                print(f"📥 Подтверждено пополнение: {phone}, {amount}")

                update_balance(phone, amount)

                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": query["from"]["id"],
                    "text": f"✅ Баланс подтверждён для {phone}"
                })

                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
                    "callback_query_id": query["id"],
                    "text": "Баланс подтверждён"
                })
            else:
                print(f"⚠️ Неверный формат callback_data: {query['data']}")
        except Exception as e:
            print("❌ Ошибка обработки callback:", str(e))
    return "OK"


@app.route("/send_notification", methods=["POST"])
def send_notification():
    body = request.json  # { "phone": "0981234567", "amount": "200" }

    keyboard = {
        "inline_keyboard": [[
            {
                "text": f"✅ Подтвердить пополнение {body['amount']} грн",
                "callback_data": json.dumps({
                    "action": "confirm",
                    "phone": body["phone"],
                    "amount": body["amount"]
                })

            }
        ]]
    }

    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
        "chat_id": ADMIN_CHAT_ID,
        "text": f"📥 Новый перевод от {body['phone']} на {body['amount']} грн",
        "reply_markup": keyboard
    })

    return "Notification sent", 200
