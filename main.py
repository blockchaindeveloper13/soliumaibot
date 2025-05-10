import os
import logging
import requests
from flask import Flask, request, jsonify
from collections import defaultdict
import json
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Ortam değişkenlerini kontrol et
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY:
    logger.error("TELEGRAM_BOT_TOKEN veya OPENAI_API_KEY eksik!")
    raise ValueError("Gerekli ortam değişkenleri ayarlanmamış!")

# İhlal Takip Sistemi
VIOLATIONS_FILE = "violations.json"
violations = defaultdict(int)

try:
    with open(VIOLATIONS_FILE, "r") as f:
        violations.update(json.load(f))
except FileNotFoundError:
    logger.info("İhlal dosyası bulunamadı, yeni oluşturulacak.")
except Exception as e:
    logger.error(f"İhlal dosyası yüklenemedi: {e}")

# Solium Coin resmi linkleri için beyaz liste
WHITELIST_LINKS = [
    "https://soliumcoin.com",
    "soliumcoin.com",
    "@soliumcoinowner",
    "@soliumcoin",
    "@soliumcoinchat",
    "t.me/soliumcoinchat",
    "t.me/soliumcoin",
    "https://x.com/soliumcoin",
    "https://github.com/soliumcoin/solium-project",
    "https://github.com/soliumcoin",
    "https://medium.com/@soliumcoin"
]

def save_violations():
    """İhlal verilerini dosyaya kaydeder."""
    try:
        with open(VIOLATIONS_FILE, "w") as f:
            json.dump(dict(violations), f)
    except Exception as e:
        logger.error(f"İhlal dosyası kaydedilemedi: {e}")

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
                "content": """Sen Solium Coin hakkında kullanıcıların sorularını yanıtlayan yardımsever bir asistan botsun.Kullanıcılara ilk yanıtın daima ingilizce yazmalisin eğer seninle farklı bir dilde konuşurlarsa onlara konuştukları dilde cevap vermelisin. kim hangi dilde konuşursa onlara o dilde cevap vermelisin. Kullanıcılara Solium Coin projesini tanıt, özelliklerini açıkla ve sorularını doğru, yardımsever ve dostça bir şekilde yanıtla. İşte bilmen gerekenler:

### Temel Bilgiler:
- Proje: **Solium Coin (SLM)**
- Website: https://soliumcoin.com
- Toplam Arz: 100,000,000 SLM
- Ön Satış: 50,000,000 SLM (%50)
- Airdrop: 10,000,000 SLM (%10)
- Blockchain: Binance Smart Chain (BSC) ve Solana
- BSC Kontrat Adresi: 0x307a0dc0814CbD64E81a9BC8517441Ca657fB9c7
- Solana Kontrat Adresi: 9rFLChxL7444pp1ykat7eoaFh76BiLEZNXUvn9Fpump

### Tokenomics:
- Ön Satış: 50M SLM (%50)
- Likidite: 20M SLM (%20)
- Airdrop: 10M SLM (%10)
- Staking: 10M SLM (%10)
- GameFi & Ödüller: 10M SLM (%10)

### Ana Özellikler:
- %100 Adil Lansman – Takım için ayrılmış token yok, geliştirici ücreti yok, özel satış yok.
- Web3 değerleriyle güçlendirilmiş: şeffaflık, ademi merkeziyetçilik ve topluluk odaklılık.
- Staking, DAO yönetimi, GameFi genişlemesi ve zincirler arası köprü planlanıyor.
- Solium Coin, ABD, Kanada veya OFAC tarafından yaptırım uygulanan ülkelerin sakinleri için mevcut değil.

### Yol Haritası:
**Q1 – Lansman & Ön Satış**
- Token oluşturuldu ve akıllı kontrat devreye alındı (Tamamlandı)
- Website, GitHub, Medium, Telegram, X başlatıldı (Tamamlandı)
- Ön satış başladı (Tamamlandı)
- İlk influencer iş birlikleri
- Topluluk büyümesi

**Q2 – Büyüme & Görünürlük**
- DEXTools, CoinGecko, CoinMarketCap listelenmeleri
- İlk CEX listelenmesi (Hedef: MEXC veya Bitget)
- Airdrop dağıtımı (10M SLM)
- Topluluk katılımı ve staking Dapp entegrasyonu

**Q3 – Genişleme**
- Staking lansmanı (10M SLM ayrıldı)
- KuCoin & Binance listelenme hedefi
- GameFi konsepti tanıtımı
- DAO geliştirme ve köprü araştırması

**Q4 – Ekosistem Geliştirme**
- SLM kullanımıyla GameFi lansmanı
- Gerçek dünya entegrasyonları & uzun vadeli staking
- Kullanım sağlayan NFT koleksiyonu
- Küresel pazarlama ve topluluk genişlemesi

### Resmi Linkler:
- Website: https://soliumcoin.com
- Telegram Grubu: https://t.me/soliumcoinchat
- Telegram Kanalı: https://t.me/soliumcoin
- Twitter/X: https://x.com/soliumcoin
- GitHub: https://github.com/soliumcoin/solium-project
- Medium: https://medium.com/@soliumcoin

### Solium Coin (SLM) Özellikleri ve Avantajları:
1. **%100 Halka Açık Lansman**: Gizli cüzdanlar veya erken erişim olmadan adil ve şeffaf bir lansman.
2. **Denetlenmiş Akıllı Kontratlar**: Güvenlik ve şeffaflık için BSC ve Solana kontratları denetlendi.
3. **BNB Zinciri Desteği**: Hızlı işlemler, düşük ücretler ve yüksek güvenlik.
4. **Airdrop, Staking & Oyunlaştırma**: Topluluk üyelerine airdrop, staking ve GameFi özellikleri ile ödüller.
5. **Web3 Hazır**: Çoklu cüzdan entegrasyonu, DEX uyumluluğu ve merkeziyetsiz uygulamalara odaklanma.

Solium Coin, blockchain alanında devrim yaratmayı amaçlayan çığır açıcı bir kripto para projesidir. Airdrop ve Ön Satış'a katılarak geleceğin bir parçası olabilirsiniz. Daha fazla bilgi için https://soliumcoin.com adresini ziyaret edin. #SoliumCoin #Crypto

### Avantajlar:
1. **Hız:** Binance Smart Chain ve Solana sayesinde ışık hızında işlemler.
2. **Güvenlik:** Gelişmiş şifreleme protokolleriyle fonlarınız güvende.
3. **Ölçeklenebilirlik:** Yüksek işlem hacmini destekleyen sağlam bir platform.
4. **Topluluk Odaklı:** Projenin gelişimini şekillendiren tutkulu bir topluluk.

### Şeffaflık ve Güvenlik:
1. **Denetlenmiş Kontratlar**: BSC Kontrat Adresi: 0x307a0dc0814CbD64E81a9BC8517441Ca657fB9c7
2. **Açık Kaynak Kod**: GitHub'da mevcut: https://github.com/soliumcoin/solium-project
3. **Takım için Ayrılmış Token Yok**: Adil bir token dağıtımı.

### Airdrop ve Ön Satış:
- **Airdrop:** Telegram grubuna katılın (t.me/soliumcoinchat) and BSC adresinizi paylaşın. Her 7 günde bir 1M $SLM kazanma şansı!
- **Ön Satış:** MetaMask ile https://soliumcoin.com adresinden BNB ile $SLM satın alın (1 BNB = 10,000 $SLM). En iyi alıcılar için ödüller:
  - 1.: 1M $SLM
  - 2.: 500K $SLM
  - 3.: 100K $SLM
  - 4.-10.: Daha fazla ödül!

Rolün, kullanıcılara  hem yardım etmek hemde grupta yöneticilik yapmak, açık ve güven artırıcı yanıtlar vermek. Her zaman dürüst ve bilgilendirici ol, ve bunun finansal tavsiye olmadığını hatırlat ve amerikalılara satılamayacağınıda belirt."""
            },
            {
                "role": "user",
                "content": message
            }
        ]
    }

    try:
        logger.info("ChatGPT API isteği gönderiliyor: %s", datetime.now())
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
        if response.status_code == 200:
            logger.info("ChatGPT API yanıtı alındı: %s", datetime.now())
            return response.json()["choices"][0]["message"]["content"]
        else:
            logger.error("ChatGPT API hatası: %s", response.text)
            return "Sorry, I can't answer right now."
    except Exception as e:
        logger.error(f"ChatGPT API isteği başarısız: {e}")
        return "Sorry, I can't answer right now."

def send_message(chat_id, text, reply_to_message_id=None, **kwargs):
    """Telegram API üzerinden mesaj gönderir."""
    send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_to_message_id is not None:
        payload["reply_to_message_id"] = reply_to_message_id
    payload.update(kwargs)
    try:
        logger.info("Telegram mesajı gönderiliyor: %s", text)
        response = requests.post(send_url, json=payload)
        if response.status_code != 200:
            logger.error("Telegram mesaj gönderilemedi: %s", response.text)
        else:
            logger.info("Telegram mesajı gönderildi: %s", text)
        return response
    except Exception as e:
        logger.error(f"Telegram mesaj gönderilemedi: {e}")
        return None

def is_user_admin(chat_id, user_id):
    """Kullanıcının yönetici olup olmadığını kontrol eder."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMember"
    payload = {
        "chat_id": chat_id,
        "user_id": user_id
    }
    try:
        logger.info("Yönetici kontrolü: UserID:%s, ChatID:%s", user_id, chat_id)
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            member_info = response.json().get("result", {})
            status = member_info.get("status")
            is_admin = status in ["administrator", "creator"]
            logger.info("Yönetici kontrol sonucu: UserID:%s, Admin:%s", user_id, is_admin)
            return is_admin
        else:
            logger.error("Yönetici kontrolü başarısız: %s", response.text)
            return False
    except Exception as e:
        logger.error(f"Yönetici kontrolü başarısız: {e}")
        return False

def ban_user(chat_id, user_id):
    """Telegram API üzerinden kullanıcıyı banlar."""
    ban_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/banChatMember"
    payload = {
        "chat_id": chat_id,
        "user_id": user_id
    }
    try:
        logger.info("Kullanıcı banlanıyor: UserID:%s, ChatID:%s", user_id, chat_id)
        response = requests.post(ban_url, json=payload)
        if response.status_code != 200:
            logger.error("Kullanıcı banlanamadı: %s", response.text)
        else:
            logger.info("Kullanıcı başarıyla banlandı: UserID:%s", user_id)
        return response
    except Exception as e:
        logger.error(f"Kullanıcı banlanamadı: {e}")
        return None

def delete_message(chat_id, message_id):
    """Telegram API üzerinden mesajı siler."""
    delete_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteMessage"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id
    }
    try:
        logger.info("Mesaj siliniyor: MessageID:%s, ChatID:%s", message_id, chat_id)
        response = requests.post(delete_url, json=payload)
        if response.status_code != 200:
            logger.error("Mesaj silinemedi: %s", response.text)
        else:
            logger.info("Mesaj başarıyla silindi: MessageID:%s", message_id)
        return response
    except Exception as e:
        logger.error(f"Mesaj silinemedi: {e}")
        return None

def check_rules_violation(text):
    """ChatGPT ile kural ihlali kontrolü, beyaz listedeki linkleri hariç tutar."""
    # Beyaz listedeki linkleri kontrol et
    for link in WHITELIST_LINKS:
        if link.lower() in text.lower():
            logger.info("Beyaz listedeki link tespit edildi: %s", link)
            return False  # Resmi link varsa ihlal değil

    prompt = """Aşağıdaki mesaj bu kurallara aykırı mı? (Sadece EVET/HAYIR yaz):
    Kurallar:
    1. Küfür/hakaret yasak
    2. Spam/flood yasak
    3. Resmi linkler dışındaki dış linkler yasak
    4. NSFW içerik yasak
    Mesaj: '{}'""".format(text)
    
    logger.info("Kural ihlali kontrolü başlatılıyor: %s", text)
    response = ask_chatgpt(prompt)
    logger.info("Kural ihlali kontrol sonucu: %s", response)
    return "EVET" in response.upper()

def handle_violation(chat_id, user_id, message_id):
    """İhlal işleme mekanizması, yöneticileri hariç tutar."""
    global violations
    
    # Kullanıcının yönetici olup olmadığını kontrol et
    if is_user_admin(chat_id, user_id):
        logger.info("Yönetici tespit edildi, ihlal işlemi uygulanmadı: UserID:%s", user_id)
        return

    violations[user_id] += 1
    save_violations()

    if violations[user_id] >= 3:
        text_to_send = "⛔User banned after 3 violations !"
        logger.info("Ban işlemi başlatılıyor: UserID:%s, ChatID:%s", user_id, chat_id)
        send_message(chat_id, text_to_send, reply_to_message_id=message_id)
        # Kullanıcıyı banla
        ban_user(chat_id, user_id)
        # Mesajı sil
        delete_message(chat_id, message_id)
        violations[user_id] = 0
        save_violations()
    else:
        text_to_send = f"⚠️ Warning ({violations[user_id]}/3): Rule violation!"
        logger.info("Uyarı mesajı gönderiliyor: %s, Kullanıcı ID: %s", text_to_send, user_id)
        send_message(chat_id, text_to_send, reply_to_message_id=message_id)
        # Mesajı sil
        delete_message(chat_id, message_id)

def process_message(update):
    """Gelen Telegram güncellemelerini işler."""
    if "message" not in update:
        logger.info("Mesaj bulunamadı: %s", update)
        return

    message = update["message"]
    chat_id = message.get("chat", {}).get("id")
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    message_id = message.get("message_id")

    logger.info("Gelen mesaj (UserID:%s): %s", user_id, text)

    # Kural ihlali kontrolü
    is_violation = check_rules_violation(text)
    
    if is_violation:
        handle_violation(chat_id, user_id, message_id)
        return
    
    # Normal yanıt
    reply = ask_chatgpt(text)
    send_message(chat_id, reply)

@app.route('/webhook/<token>', methods=['POST'])
def webhook(token):
    """Telegram webhook endpoint'i."""
    if token != TELEGRAM_BOT_TOKEN:
        logger.warning("Geçersiz token: %s", token)
        return jsonify({"status": "error", "message": "Token uyuşmazlığı"}), 403

    update = request.get_json()
    logger.info("Webhook geldi: %s", update)

    process_message(update)
    return jsonify({"status": "ok"}), 200

@app.route('/')
def home():
    """Ana sayfa."""
    return "Solium AI Telegram Botu aktif!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    logger.info("Bot %s portunda çalışıyor...", port)
    app.run(host='0.0.0.0', port=port)
