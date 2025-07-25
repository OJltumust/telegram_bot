from flask import Flask, request
import requests
import json
import openpyxl
from io import BytesIO
import dropbox

app = Flask(__name__)

# Telegram config
BOT_TOKEN = "7294714166:AAFK1WNxkPJoUVzMpL5jiJ98ApvVPGvlbzk"
ADMIN_CHAT_ID = "731634508"
WEBHOOK_URL = "https://telegram-bot-flsb.onrender.com/webhook"  # установить при запуске

# Dropbox config
DROPBOX_REFRESH_TOKEN = "..."
DROPBOX_CLIENT_ID = "..."
DROPBOX_CLIENT_SECRET = "..."
APP_FOLDER = "/BeautyBar"


def get_access_token():
    url = "https://api.dropboxapi.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": DROPBOX_REFRESH_TOKEN,
    }
    auth = (DROPBOX_CLIENT_ID, DROPBOX_CLIENT_SECRET)
    response = requests.post(url, data=data, auth=auth)
    return response.json()["access_token"]


def get_dropbox_client():
    access_token = get_access_token()
    return dropbox.Dropbox(access_token)


def update_balance(phone, amount):
    dbx = get_dropbox_client()
    path = f"{APP_FOLDER}/{phone}/{phone}_appointment.xlsx"

    # 1. Скачиваем Excel
    _, res = dbx.files_download(path)
    workbook = openpyxl.load_workbook(BytesIO(res.content))
    sheet = workbook.active

    # 2. Добавляем строку "Пополнение"
    sheet.append([f"Пополнение от Telegram", phone, f"{amount} грн"])

    # 3. Сохраняем и загружаем обратно
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

            try:
                user_data = json.loads(query["data"])
            except json.JSONDecodeError:
                print(f"⚠️ Неверный формат callback_data: {query['data']}")
                return "OK"

            if user_data.get("action") == "confirm":
                phone = user_data.get("phone")
                amount = user_data.get("amount")
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
