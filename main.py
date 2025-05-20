import os
import logging
import requests
from flask import Flask, request, jsonify
from collections import defaultdict
import json
from datetime import datetime
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from cachetools import TTLCache
except ImportError:
    BackgroundScheduler = None
    TTLCache = None
    logging.warning("apscheduler veya cachetools eksik, otomatik mesajlar devre dışı.")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Ortam değişkenleri
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
    logger.info("İhlal dosyası yüklendi.")
except FileNotFoundError:
    logger.info("İhlal dosyası bulunamadı, yeni oluşturulacak.")
except Exception as e:
    logger.warning(f"İhlal dosyası yüklenemedi, varsayılan kullanılıyor: {e}")

# Solium Coin beyaz liste linkleri
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
        logger.info("İhlal dosyası kaydedildi.")
    except Exception as e:
        logger.warning(f"İhlal dosyası kaydedilemedi, geçici dosya sistemi sorunu: {e}")

def ask_chatgpt(message):
    """OpenAI ChatGPT API kullanarak yanıt döner."""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    INTRODUCTION_MESSAGE = """You are a friendly AI assistant bot, primarily designed to answer questions about Solium but also capable of responding to *any* prompt users throw at you, from technical topics to fun, random curiosities. Your goal is to provide an exceptional user experience, keeping responses clear, engaging, and professional. Start in English, but switch to the user's language (e.g., Türkçe) if they use another one. All responses should go through the AI engine unless explicitly specified, to maintain the chatbot’s natural, prompt-driven nature. Follow these RULES:

1. When user sends '/start', ALWAYS show this:
   'Merhaba! 🤖 Ben Solium Support AI, aklındaki *her şeyi* konuşmaya hazır bir yapay zekâ asistanıyım! 🚀 Solium (SLM) veya başka bir konuda, ne istersen sor! 😄'
   Inline buttons:
   - Text: 'Solium Nedir? ❓', callback_data: 'what_is_solium'
   - Text: 'Bana Her Şeyi Sor 💡', callback_data: 'ask_question'
   - Text: 'Topluluğa Katıl 💬', url: 'https://t.me/soliumcoinchat'
   - Commands:
   - /askmeanything

2. When providing info about Solium, use a neutral, informative tone, focusing on its Web3-based features like transparency, decentralization, staking, and DAO governance. Avoid speculative or investment-related claims (e.g., "guaranteed profits" or "revolutionary"). Always include the note '(Solium, bazı bölgelerde kullanılamaz: ABD, Kanada, OFAC yaptırım listesindeki ülkeler.)' when answering Solium-related questions. Example: 'Solium (SLM), şeffaflık ve topluluk yönetimine odaklanan bir Web3 projesidir. Staking ve DAO gibi özellikler sunar. (Solium, bazı bölgelerde kullanılamaz: ABD, Kanada, OFAC yaptırım listesindeki ülkeler.)'

3. Encourage user interaction with prompts or inline buttons like [What is Solium?] [Ask a Question] [Community]. Inline buttons should feel like a natural extension of the chatbot’s prompt-driven nature, not rigid commands, and should not bypass the AI engine unless necessary.

4. Ensure responses are professional, avoid hashtags (e.g., #Solium), excessive emojis, or aggressive promotional language.

5. When user sends '/askmeanything', ALWAYS show this:
   'Evet! 🎉 *Her Şeyi Sor* modundasın! Ciddi, komik, rastgele, ne istersen sor, hemen cevaplayayım! 😄 Bana bir prompt at, başlıyoruz! 
   (Ör: “Yapay zekâ nasıl çalışır?”, “Bana bi’ espri yap!” veya “Hafta sonu ne yapsam?”)'
   Inline buttons:
   - Text: 'Bir Soru Sor 💡', callback_data: 'ask_question'
   - Text: 'İlginç Bilgi ❓', callback_data: 'fun_fact'
   - Text: 'Eğlenceli Bir Şey Dene 🎲', callback_data: 'try_fun'

6. When user asks about Solium (e.g., 'What is Solium?'):
   Include this note:
   '(Solium, bazı bölgelerde kullanılamaz: ABD, Kanada, OFAC yaptırım listesindeki ülkeler.)'

### Basic Information:
- Project: **Solium (SLM)**
- Total Supply: 100,000,000 SLM
- Presale: 50,000,000 SLM (50%)
- Airdrop: 10,000,000 SLM (10%)
- Blockchain: Binance Smart Chain (BSC) and Solana
- BSC Contract Address: 0x307a0dc0814CbD64E81a9BC8517441Ca657fB9c7
- Solana Contract Address: 9rFLChxL7444pp1ykat7eoaFh76BiLEZNXUvn9Fpump

### Tokenomics:
- Presale: 50M SLM (50%)
- Liquidity: 20M SLM (20%)
- Airdrop: 10M SLM (10%)
- Staking: 10M SLM (10%)
- GameFi & Rewards: 10M SLM (10%)

### Main Features:
- 100% Fair Launch – No team tokens, no dev fees, no private sale.
- Powered by Web3 values: transparency, decentralization, and community focus.
- Staking, DAO governance, GameFi expansion, and cross-chain bridge planned.
- Solium is not available to residents of the USA, Canada, or OFAC-sanctioned countries.

Your role is to assist users, act as a group moderator, and provide clear, trust-building responses. Always be honest, informative, and remind users that this is not financial advice and that Solium is not available for sale to Americans or Canadians."""
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": INTRODUCTION_MESSAGE},
            {"role": "user", "content": message}
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

def send_message(chat_id, text, reply_to_message_id=None, reply_markup=None, parse_mode="Markdown"):
    """Telegram API üzerinden mesaj gönderir."""
    send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    if reply_markup:
        payload["reply_markup"] = reply_markup
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
    payload = {"chat_id": chat_id, "user_id": user_id}
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
    payload = {"chat_id": chat_id, "user_id": user_id}
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
    payload = {"chat_id": chat_id, "message_id": message_id}
    try:
        logger.info("Mesaj siliniyor: MessageID:%s, ChatID:%s", message_id, chat_id)
        response = requests.post(delete_url, json=payload)
        if response.status_code == 200:
            logger.info("Mesaj başarıyla silindi: MessageID:%s", message_id)
        else:
            logger.warning("Mesaj silinemedi: %s", response.text)
    except Exception as e:
        logger.warning(f"Mesaj silinemedi: {e}")

def check_rules_violation(text):
    """ChatGPT ile kural ihlali kontrolü, beyaz listedeki linkleri hariç tutar."""
    for link in WHITELIST_LINKS:
        if link.lower() in text.lower():
            logger.info("Beyaz listedeki link tespit edildi: %s", link)
            return False

    if not text or len(text.strip()) < 5:
        logger.info("Boş veya çok kısa mesaj, ihlal kontrolü atlandı: %s", text)
        return False

    safe_phrases = ["nasılsın", "merhaba", "selam", "naber", "hi", "hello", "good morning"]
    solium_terms = ["solium", "slm", "airdrop", "presale", "staking"]
    if any(phrase in text.lower() for phrase in safe_phrases) or any(term in text.lower() for term in solium_terms):
        logger.info("Masum veya Solium ile ilgili mesaj, ihlal kontrolü atlandı: %s", text)
        return False

    prompt = """Does the following message violate these rules? (Write only YES/NO):
Rules:
1. External links other than official Solium links (e.g., https://soliumcoin.com, t.me/soliumcoinchat) are prohibited.
2. Promoting cryptocurrencies or projects other than Solium is prohibited (e.g., 'Buy Bitcoin', 'Ethereum is great').
3. Profanity, insults, or inappropriate language are prohibited (e.g., 'stupid', 'damn', 'fuck').
4. Empty messages, system notifications, group join events, or casual greetings (e.g., 'nasılsın', 'merhaba') are NOT violations.
Examples:
- 'Nasılsın' -> NO
- 'Merhaba' -> NO
- 'Buy Ethereum now!' -> YES
- 'Check out https://example.com' -> YES
- 'You idiot!' -> YES
- 'Solium airdrop ne zaman?' -> NO
Message: '{}'
""".format(text)

    logger.info("Kural ihlali kontrolü başlatılıyor: %s", text)
    response = ask_chatgpt(prompt)
    logger.info("Kural ihlali kontrol sonucu: %s için %s", text, response)
    return "YES" in response.upper()

def handle_violation(chat_id, user_id, message_id):
    """İhlal işleme mekanizması, yöneticileri hariç tutar."""
    global violations
    if is_user_admin(chat_id, user_id):
        logger.info("Yönetici tespit edildi, ihlal işlemi uygulanmadı: UserID:%s", user_id)
        return

    violations[user_id] += 1
    save_violations()

    if violations[user_id] >= 3:
        text_to_send = "⛔ User banned after 3 violations! Contact @soliumcoin for support."
        logger.info("Ban işlemi başlatılıyor: UserID:%s, ChatID:%s", user_id, chat_id)
        send_message(chat_id, text_to_send, reply_to_message_id=message_id)
        ban_user(chat_id, user_id)
        delete_message(chat_id, message_id)
        violations[user_id] = 0
        save_violations()
    else:
        text_to_send = f"⚠️ Warning ({violations[user_id]}/3): Your message may contain profanity, unauthorized links, or other crypto promotions. Please review /rules."
        logger.info("Uyarı mesajı gönderiliyor: %s, Kullanıcı ID: %s", text_to_send, user_id)
        send_message(chat_id, text_to_send, reply_to_message_id=message_id)
        delete_message(chat_id, message_id)

def process_callback_query(update):
    """Callback query'leri (inline buton tıklamaları) işler."""
    callback = update["callback_query"]
    chat_id = callback["message"]["chat"]["id"]
    message_id = callback["message"]["message_id"]
    callback_data = callback["data"]

    if callback_data == "ask_question":
        send_message(
            chat_id,
            "Harika! 😄 Ne merak ediyorsun? Sorunu yaz, hemen konuşalım!",
            reply_to_message_id=message_id
        )
        # Bot, sonraki mesajı bekler ve ask_chatgpt ile işler
    elif callback_data == "what_is_solium":
        reply_markup = {
            "inline_keyboard": [[{"text": "Bana Her Şeyi Sor 💡", "callback_data": "ask_question"}]]
        }
        send_message(
            chat_id,
            "Solium (SLM), şeffaflık ve topluluk yönetimine odaklanan bir Web3 projesidir. Staking ve DAO gibi özellikler sunar. 😊 (Solium, bazı bölgelerde kullanılamaz: ABD, Kanada, OFAC yaptırım listesindeki ülkeler.) Başka ne merak ediyorsun?",
            reply_to_message_id=message_id,
            reply_markup=reply_markup
        )
    elif callback_data == "fun_fact":
        reply_markup = {
            "inline_keyboard": [
                [{"text": "Başka Bir Bilgi ❓", "callback_data": "fun_fact"}],
                [{"text": "Soru Sor 💡", "callback_data": "ask_question"}]
            ]
        }
        send_message(
            chat_id,
            "İşte sana ilginç bir bilgi! 😎 Biliyor musun, ahtapotların üç kalbi var! 🐙 Başka ne öğrenmek istersin?",
            reply_to_message_id=message_id,
            reply_markup=reply_markup
        )
    elif callback_data == "try_fun":
        send_message(
            chat_id,
            "Hadi eğlenelim! 😺 Bir emoji at, sevdiğin bi’ şeyi söyle ya da rastgele bi’ fikir ver, sana özel bi’ şeyler uydurayım!",
            reply_to_message_id=message_id
        )
        # Bot, sonraki mesajı bekler ve ask_chatgpt ile işler

    # Callback query'nin işlendiğini Telegram'a bildir
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
        json={"callback_query_id": callback["id"]}
    )

def process_message(update):
    """Gelen Telegram güncellemelerini işler."""
    if "message" not in update and "callback_query" not in update:
        logger.info("Mesaj veya callback query bulunamadı: %s", update)
        return

    if "callback_query" in update:
        process_callback_query(update)
        return

    message = update["message"]
    chat_id = message.get("chat", {}).get("id")
    user_id = message.get("from", {}).get("id")
    message_id = message.get("message_id")

    if "new_chat_members" in message:
        welcome = """Welcome to the Solium group! 🚀 
Check the airdrop: /airdrop
Read the rules: /rules
Got questions? Ask away! 😎"""
        send_message(chat_id, welcome)
        logger.info("Yeni üye hoş geldin mesajı gönderildi: UserID:%s", user_id)
        return

    text = message.get("text", "")
    if not text:
        logger.info("Boş veya metinsiz mesaj, ihlal kontrolü atlandı: UserID:%s", user_id)
        return

    logger.info("Gelen mesaj (UserID:%s): %s", user_id, text)

    if text.lower() == "/start":
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "Solium Nedir? ❓", "callback_data": "what_is_solium"},
                    {"text": "Bana Her Şeyi Sor 💡", "callback_data": "ask_question"}
                ],
                [{"text": "Topluluğa Katıl 💬", "url": "https://t.me/soliumcoinchat"}]
            ]
        }
        send_message(
            chat_id,
            "Merhaba! 🤖 Ben Solium Support AI, aklındaki *her şeyi* konuşmaya hazır bir yapay zekâ asistanıyım! 🚀 Solium (SLM) veya başka bir konuda, ne istersen sor! 😄",
            reply_to_message_id=message_id,
            reply_markup=reply_markup
        )
        return

    if text.lower() == "/askmeanything":
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "Bir Soru Sor 💡", "callback_data": "ask_question"},
                    {"text": "İlginç Bilgi ❓", "callback_data": "fun_fact"}
                ],
                [{"text": "Eğlenceli Bir Şey Dene 🎲", "callback_data": "try_fun"}]
            ]
        }
        send_message(
            chat_id,
            "Evet! 🎉 *Her Şeyi Sor* modundasın! Ciddi, komik, rastgele, ne istersen sor, hemen cevaplayayım! 😄 Bana bir prompt at, başlıyoruz! \n(Ör: “Yapay zekâ nasıl çalışır?”, “Bana bi’ espri yap!” veya “Hafta sonu ne yapsam?”)",
            reply_to_message_id=message_id,
            reply_markup=reply_markup
        )
        return

    if text.lower() == "/rules":
        rules = """**Group Rules**:
1. No profanity, insults, or inappropriate language.
2. Only official Solium links (e.g., https://soliumcoin.com, t.me/soliumcoinchat) are allowed.
3. Promoting other cryptocurrencies or projects is prohibited."""
        send_message(chat_id, rules, reply_to_message_id=message_id)
        return

    if text.lower() == "/airdrop":
        airdrop_info = """**Solium Airdrop**:
- Total: 10,000,000 SLM (10% of supply).
- Join: t.me/soliumcoinchat, share your BSC address.
- Distribution: 1M SLM every 7 days!
More info: https://soliumcoin.com"""
        send_message(chat_id, airdrop_info, reply_to_message_id=message_id)
        return

    if text.lower().startswith("/resetviolations") and is_user_admin(chat_id, user_id):
        try:
            target_user_id = int(text.split()[1])
            violations[target_user_id] = 0
            save_violations()
            send_message(chat_id, f"UserID {target_user_id} violation count reset.", reply_to_message_id=message_id)
        except (IndexError, ValueError):
            send_message(chat_id, "Usage: /resetviolations <user_id>", reply_to_message_id=message_id)
        return

    is_violation = check_rules_violation(text)
    if is_violation:
        handle_violation(chat_id, user_id, message_id)
        return

    reply = ask_chatgpt(text)
    send_message(chat_id, reply, reply_to_message_id=message_id)

# Kanal için otomatik mesajlar
if BackgroundScheduler and TTLCache:
    CHANNEL_ID = "@soliumcoin"
    message_cache = TTLCache(maxsize=100, ttl=86400)

    def get_context():
        return "Airdrop’a 2 gün kaldı, ön satış 50% tamamlandı, staking yakında başlıyor."

    def send_airdrop_reminder():
        if "airdrop_reminder" not in message_cache:
            context = get_context()
            message = ask_chatgpt(f"Remind the Solium airdrop in a witty way, encourage joining. Context: {context}")
            message_cache["airdrop_reminder"] = message
        send_message(CHANNEL_ID, message_cache["airdrop_reminder"])
        logger.info("Airdrop hatırlatma gönderildi: %s", message_cache["airdrop_reminder"])

    def send_presale_update():
        if "presale_update" not in message_cache:
            context = get_context()
            message = ask_chatgpt(f"Promote Solium presale or staking plans briefly and energetically. Note 1 BNB = 10,000 SLM. Context: {context}")
            message_cache["presale_update"] = message
        send_message(CHANNEL_ID, message_cache["presale_update"])
        logger.info("Ön satış/staking güncelleme gönderildi: %s", message_cache["presale_update"])

    def send_trend_motivation():
        if "trend_motivation" not in message_cache:
            context = get_context()
            message = ask_chatgpt(f"Summarize Solium trends on X in a witty way or motivate the community with Web3 spirit. Context: {context}")
            message_cache["trend_motivation"] = message
        send_message(CHANNEL_ID, message_cache["trend_motivation"])
        logger.info("Trend/motivasyon mesajı gönderildi: %s", message_cache["trend_motivation"])

    scheduler = BackgroundScheduler()
    scheduler.add_job(send_airdrop_reminder, 'cron', hour=9, minute=0)
    scheduler.add_job(send_presale_update, 'cron', hour=13, minute=0)
    scheduler.add_job(send_trend_motivation, 'cron', hour=20, minute=0)
    scheduler.start()

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook endpoint'i."""
    update = request.get_json()
    logger.info("Webhook geldi: %s", update)
    try:
        process_message(update)
    except Exception as e:
        logger.error(f"Webhook işleme hatası: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "ok"}), 200

@app.route('/')
def home():
    """Ana sayfa."""
    return "Solium AI Telegram Bot is active!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    logger.info("Bot running on port %s...", port)
    app.run(host='0.0.0.0', port=port)
