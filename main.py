import os
import logging
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Ortam değişkenlerinden tokenları çekelim.
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')  # İlerleyen aşamalarda kullanabilirsiniz.

def send_message(chat_id, text):
    """Telegram API kullanarak mesaj gönderir."""
    send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    response = requests.post(send_url, json=payload)
    if response.status_code != 200:
        logger.error("Mesaj gönderilemedi. Durum kodu: %s, Yanıt: %s", response.status_code, response.text)
    return response

def process_message(update):
    """Gelen mesajı işleyip yanıt üretir."""
    # Telegram güncellemesinde 'message' alanı olması gerekiyor.
    if "message" not in update:
        logger.info("Güncellemede 'message' alanı yok: %s", update)
        return
    message = update["message"]
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "")
    logger.info("Chat ID: %s, Mesaj: %s", chat_id, text)

    # Basit bir örnek: Eko (echo) yaparak gelen mesajı geri gönder.
    response_text = f"Mesajınız: {text}"
    send_message(chat_id, response_text)

@app.route('/webhook/<token>', methods=['POST'])
def webhook(token):
    # Güvenlik kontrolü: URL'de bulunan token ile ortam değişkenindeki token eşleşmeli.
    if token != TELEGRAM_BOT_TOKEN:
        logger.error("Token uyuşmuyor: Gelen=%s, Beklenen=%s", token, TELEGRAM_BOT_TOKEN)
        return jsonify({"status": "error", "message": "Geçersiz token"}), 403

    update = request.get_json()
    logger.info("Gelen güncelleme: %s", update)
    
    # Gelen mesajı işle
    process_message(update)
    
    # Telegram'ın webhook çağrısına 200 OK yanıtı dönmek yeterli.
    return jsonify({"status": "ok"}), 200

@app.route('/', methods=['GET'])
def home():
    return "Solium Coin Telegram Bot çalışıyor!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    logger.info("Uygulama %s portunda başlatılıyor...", port)
    app.run(host='0.0.0.0', port=port)
