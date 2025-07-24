from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# Хранилище пополнений (в реальности - база или кеш)
pending_topups = {}

@app.route("/", methods=["POST"])
def telegram_webhook():
    data = request.get_json()

    if "message" in data and "text" in data["message"]:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message["text"]

        if text.startswith("/start"):
            send_message(chat_id, "Бот запущен ✅")
        return "ok"

    elif "callback_query" in data:
        query = data["callback_query"]
        user_id = query["from"]["id"]
        data_id = query["data"]  # userPhone

        if data_id in pending_topups:
            amount = pending_topups[data_id]["amount"]
            confirm_topup(data_id, amount)
            send_message(user_id, f"✅ Пополнение {amount} грн подтверждено.")
            del pending_topups[data_id]

        return "ok"

    return "no-action"

# 📩 Отправка сообщения с кнопкой "Подтвердить"
def send_topup_notification(userPhone, amount):
    pending_topups[userPhone] = {"amount": amount}
    message = f"💰 Пополнение {amount} грн для пользователя {userPhone}"
    inline_keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Подтвердить", "callback_data": userPhone}
        ]]
    }

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": ADMIN_CHAT_ID,
        "text": message,
        "reply_markup": inline_keyboard
    })

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

# Твой метод подтверждения (например, изменить SharedPreferences или Firebase)
def confirm_topup(userPhone, amount):
    print(f"Пополнение {userPhone} на {amount} грн подтверждено админом")
    # тут вызывай код обновления баланса
    # например, по API или через Room, если нужно

@app.route("/", methods=["GET"])
def index():
    return "Hello from Flask Telegram Bot!"

