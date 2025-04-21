import os
import logging
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Ortam değişkenlerinden tokenları çekelim.
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# --- ChatGPT'den yanıt alma fonksiyonu ---
def ask_chatgpt(message):
    """OpenAI ChatGPT API kullanarak yanıt döner."""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": "Sen Solium Coin hakkında kullanıcıların sorularını yanıtlayan yardımsever bir asistan botsun."
            },
            {
                "role": "user",
                "content": message
            }
        ]
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        logger.error("ChatGPT API hatası: %s", response.text)
        return "Üzgünüm, şu anda yanıt veremiyorum."

# --- Telegram'a mesaj gönderme fonksiyonu ---
def send_message(chat_id, text):
    """Telegram API üzerinden mesaj gönderir."""
    send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    response = requests.post(send_url, json=payload)
    if response.status_code != 200:
        logger.error("Telegram mesaj gönderilemedi: %s", response.text)
    return response

# --- Mesaj işleme fonksiyonu ---
def process_message(update):
    if "message" not in update:
        logger.info("Mesaj bulunamadı: %s", update)
        return

    message = update["message"]
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    logger.info("Gelen mesaj: %s", text)

    # OpenAI GPT'den yanıt al
    reply = ask_chatgpt(text)

    # Yanıtı gönder
    send_message(chat_id, reply)

# --- Webhook endpoint ---
@app.route('/webhook/<token>', methods=['POST'])
def webhook(token):
    if token != TELEGRAM_BOT_TOKEN:
        return jsonify({"status": "error", "message": "Token uyuşmazlığı"}), 403

    update = request.get_json()
    logger.info("Webhook geldi: %s", update)

    process_message(update)
    return jsonify({"status": "ok"}), 200

# --- Ana Sayfa ---
@app.route('/')
def home():
    return "Solium AI Telegram Botu aktif!"

# --- Sunucuyu başlat ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    logger.info("Bot %s portunda çalışıyor...", port)
    app.run(host='0.0.0.0', port=port)
