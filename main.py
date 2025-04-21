import os
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Webhook endpoint: Gelen güncellemeleri alır.
@app.route('/webhook/<token>', methods=['POST'])
def webhook(token):
    # Güvenlik amaçlı: İstekle gönderilen token,
    # Heroku’da tanımlı ortam değişkenindeki token ile eşleşmeli.
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if token != bot_token:
        logger.error("Token uyuşmuyor: Gelen=%s, Beklenen=%s", token, bot_token)
        return jsonify({"status": "error", "message": "Geçersiz token"}), 403

    update = request.get_json()
    logger.info("Gelen güncelleme: %s", update)

    # Burada update içeriğine göre çeşitli işlemler yapabilirsiniz
    # Örneğin, /start gibi komutlara yanıt verebilir veya mesaj işleyebilirsiniz.
    
    # Şimdilik sadece OK yanıtı dönüyoruz.
    return jsonify({"status": "ok"}), 200

# Basit ana sayfa: Uygulamanın Heroku’da çalıştığını kontrol etmek için.
@app.route('/', methods=['GET'])
def home():
    return "Solium Coin Telegram Bot çalışıyor!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    logger.info("Uygulama %s portunda başlatılıyor...", port)
    app.run(host='0.0.0.0', port=port)
