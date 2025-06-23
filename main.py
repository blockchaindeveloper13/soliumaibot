# -*- coding: utf-8 -*-
import os
import logging
import requests
from flask import Flask, request, jsonify
from collections import defaultdict, deque
import json
import random
from datetime import datetime
from openai import OpenAI
from collections import namedtuple

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask uygulaması
app = Flask(__name__)

# Environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY:
    logger.error("TELEGRAM_BOT_TOKEN or OPENAI_API_KEY missing!")
    raise ValueError("Required environment variables not set!")

# Initialize clients
client = OpenAI(api_key=OPENAI_API_KEY)

# Data structures
Response = namedtuple('Response', ['output_text'])
violations = defaultdict(int)
conversations = defaultdict(lambda: deque(maxlen=100))

# Whitelist
WHITELIST_LINKS = [
    "https://soliumcoin.com",
    "soliumcoin.com",
    "@soliumcoinowner",
    "@soliumcoin",
    "https://t.me/+KDhk3UEwZAg3MmU0",
    "t.me/soliumcoin",
    "https://x.com/soliumcoin",
    "https://github.com/soliumcoin/solium-project",
    "https://github.com/soliumcoin",
    "https://medium.com/@soliumcoin"
]

def ask_chatgpt(message, user_id=None):
    """OpenAI API ile mesaj işleme"""
    INTRODUCTION_MESSAGE = """[Önceki uzun sistem mesajınız buraya aynen gelecek]"""
    
    messages = [{"role": "system", "content": INTRODUCTION_MESSAGE}]
    
    if user_id and user_id in conversations:
        recent_conversation = list(conversations[user_id])[-10:]
        context = "\n".join([f"{msg['timestamp']}: {msg['text']}" for msg in recent_conversation])
        messages.append({
            "role": "system",
            "content": f"Conversation history:\n{context}"
        })
    
    messages.append({"role": "user", "content": message})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=500
        )
        return Response(output_text=response.choices[0].message.content)
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return Response(output_text="Üzgünüm, bir hata oluştu.")

def send_message(chat_id, text, reply_to_message_id=None, reply_markup=None):
    """Telegram mesaj gönderme"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return None

def is_user_admin(chat_id, user_id):
    """Kullanıcı admin mi kontrolü"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMember"
    payload = {"chat_id": chat_id, "user_id": user_id}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            status = response.json().get("result", {}).get("status")
            return status in ["administrator", "creator"]
        return False
    except Exception as e:
        logger.error(f"Admin check error: {e}")
        return False

def ban_user(chat_id, user_id):
    """Kullanıcıyı banlama"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/banChatMember"
    payload = {"chat_id": chat_id, "user_id": user_id}
    
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Ban error: {e}")
        return False

def delete_message(chat_id, message_id):
    """Mesaj silme"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteMessage"
    payload = {"chat_id": chat_id, "message_id": message_id}
    
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Delete message error: {e}")
        return False

def check_rules_violation(text):
    """Kural ihlali kontrolü"""
    # Whitelist kontrolü
    for link in WHITELIST_LINKS:
        if link.lower() in text.lower():
            return False
    
    # Kısa mesaj kontrolü
    if len(text.strip()) < 5:
        return False
    
    # Güvenli ifadeler
    safe_phrases = ["nasılsın", "merhaba", "selam", "naber"]
    if any(phrase in text.lower() for phrase in safe_phrases):
        return False
    
    # OpenAI ile ihlal kontrolü
    prompt = f"Bu mesaj kural ihlali içeriyor mu? (Sadece EVET/HAYIR): {text}"
    response = ask_chatgpt(prompt).output_text
    return "EVET" in response.upper()

def handle_violation(chat_id, user_id, message_id):
    """İhlal işleme"""
    if is_user_admin(chat_id, user_id):
        return
    
    violations[user_id] += 1
    
    if violations[user_id] >= 3:
        send_message(chat_id, "⛔ 3 ihlal! Kullanıcı banlandı.", reply_to_message_id=message_id)
        ban_user(chat_id, user_id)
        violations[user_id] = 0
    else:
        warning = f"⚠️ Uyarı ({violations[user_id]}/3): Kuralları ihlal etmeyin!"
        send_message(chat_id, warning, reply_to_message_id=message_id)
    
    delete_message(chat_id, message_id)

def process_callback(update):
    """Callback işleme"""
    callback = update["callback_query"]
    chat_id = callback["message"]["chat"]["id"]
    message_id = callback["message"]["message_id"]
    data = callback["data"]
    
    if data == "ask_question":
        send_message(chat_id, "Sorunuzu yazın:", reply_to_message_id=message_id)
    # Diğer callback işlemleri...

def process_message(update):
    """Mesaj işleme"""
    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    user_id = message.get("from", {}).get("id")
    message_id = message.get("message_id")
    text = message.get("text", "")
    
    # Mesaj geçmişine ekle
    if text:
        conversations[user_id].append({
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
    
    # Komut işleme
    if text.startswith("/"):
        if text.lower() == "/start":
            # Başlangıç mesajı gönder
            pass
        elif text.lower() == "/rules":
            # Kuralları gönder
            pass
        # Diğer komutlar...
        return
    
    # İhlal kontrolü
    if check_rules_violation(text):
        handle_violation(chat_id, user_id, message_id)
        return
    
    # AI yanıtı
    if "rose" in text.lower() or "admin" in text.lower():
        response = ask_chatgpt(text, user_id)
        send_message(chat_id, response.output_text, reply_to_message_id=message_id)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook handler"""
    try:
        update = request.get_json()
        logger.info(f"Received update: {update}")
        
        if "message" in update:
            process_message(update)
        elif "callback_query" in update:
            process_callback(update)
            
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/')
def home():
    """Health check"""
    return "Bot is running"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
