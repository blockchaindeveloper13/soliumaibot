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
import httpx

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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

# OpenAI client initialization
try:
    client = OpenAI(
        api_key=OPENAI_API_KEY,
        http_client=httpx.Client(timeout=60.0)
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"OpenAI client init failed: {e}")
    raise

# Data structures
Response = namedtuple('Response', ['output_text'])
violations = defaultdict(int)
conversations = defaultdict(lambda: deque(maxlen=100))

# Whitelist links
WHITELIST_LINKS = [
    "https://soliumcoin.com",
    "soliumcoin.com",
    "@soliumcoinowner",
    "@soliumcoin",
    "https://t.me/+KDhk3UEwZAg3MmU0"
]

def ask_chatgpt(message, user_id=None):
    """Optimized OpenAI API call with error handling"""
    try:
        messages = [{
            "role": "system",
            "content": "You are a helpful AI assistant. Respond concisely."
        }]
        
        if user_id in conversations:
            context = "\n".join([msg['text'] for msg in conversations[user_id]][-5:])
            messages.append({
                "role": "system",
                "content": f"Context:\n{context}"
            })
            
        messages.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=300,
            timeout=30  # 30 second timeout
        )
        return Response(output_text=response.choices[0].message.content)
        
    except Exception as e:
        logger.error(f"ChatGPT error: {e}")
        return Response(output_text="Sorry, I encountered an error. Please try again.")

def send_telegram_message(chat_id, text, reply_to=None):
    """Robust Telegram message sending"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text[:4000],  # Truncate long messages
            "parse_mode": "Markdown"
        }
        if reply_to:
            payload["reply_to_message_id"] = reply_to
            
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False

@app.route('/webhook', methods=['POST'])
def webhook():
    """Main webhook handler"""
    try:
        update = request.get_json()
        
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            
            # Basic command handling
            if text.startswith("/start"):
                send_telegram_message(chat_id, "Bot is ready!")
                return jsonify({"status": "ok"})
                
            # AI response
            if "rose" in text.lower() or "admin" in text.lower():
                response = ask_chatgpt(text)
                send_telegram_message(chat_id, response.output_text)
                
        return jsonify({"status": "ok"})
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/')
def health_check():
    """Health check endpoint"""
    return "Bot is running"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
