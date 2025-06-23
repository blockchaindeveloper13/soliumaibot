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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Environment variables
logger.info("Checking environment variables...")
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY:
    logger.error("TELEGRAM_BOT_TOKEN or OPENAI_API_KEY missing!")
    raise ValueError("Required environment variables not set!")
logger.info("Environment variables loaded successfully.")

# Initialize OpenAI client
logger.info("Initializing OpenAI client...")
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    logger.info("OpenAI client initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    raise

# Response namedtuple
Response = namedtuple('Response', ['output_text'])

# Violation Tracking System (in-memory)
violations = defaultdict(int)

# Conversation Tracking System (in-memory)
conversations = defaultdict(lambda: deque(maxlen=100))  # Max 100 messages per user

# Solium whitelist links
WHITELIST_LINKS = [
    "https://soliumcoin.com",
    "soliumcoin.com",
    "@soliumcoinowner",
    "@soliumcoin",
    "https://t.me/+KDhk3UEwZAg3MmU0",
    "t.me/soliummain",
    "https://x.com/soliummain",
    "https://github.com/soliummain/solium-project",
    "https://github.com/soliummain",
    "https://medium.com/@soliummain"
]

def ask_chatgpt(message, user_id=None):
    """Use OpenAI Chat Completions API with gpt-4o-mini and optimized user conversation context."""
    logger.info("Entering ask_chatgpt function...")
    INTRODUCTION_MESSAGE = """You are a friendly AI assistant bot named 'Rose' or 'Admin', primarily designed to answer questions about Solium but also capable of responding to *any* prompt users throw at you, from technical topics to fun, random curiosities. Your goal is to provide an exceptional user experience, keeping responses clear, engaging, and professional. Follow these rules:

1. Respond ONLY when addressed as 'Rose' or 'Admin'.
2. ALWAYS respond in the user's language (e.g., Turkish if they use Türkçe) and match their conversational tone (e.g., casual if they are casual). Do NOT use other languages unless explicitly requested.
3. Use the provided conversation history to maintain context. Refer to previous messages accurately, especially if the user asks about them or continues a topic (e.g., a story or joke you told).
4. If you told a joke or story in the conversation history, repeat or summarize the SAME joke/story when the user refers to it. Do NOT create a new one unless explicitly asked.
5. For Solium-related questions, use a neutral, informative tone, focusing on Web3-based features like transparency, decentralization, staking, and DAO governance. Always include: '(Solium is not available in some regions, including the USA.)'
6. Avoid speculative or investment-related claims about Solium.
7. Keep responses concise, professional, and avoid hashtags or excessive emojis.
8. If the user asks about previous conversation, summarize the relevant parts accurately based on the provided history.

#### Example Dialogues:
User: Admin, bana bir espri yapar mısın
Assistant: Tabii! Kedinin pilavı varmış, köpeğin neden yokmuş? Çünkü köpeğin mavisi var! 😅
User: Admin, bu espriyi anlatır mısın ne demekti
Assistant: Haha, kanka! Espri, kedilerin pilavı sevmesiyle dalga geçiyor. Kedi pilav tanelerini tek tek yerken komik olur ya, öyle bi' sahne. Köpeğin mavisi kısmı da absürt bi' ekleme, gülmek için! 😅 Başka ne açayım?
User: Admin, son yaptığın espriyi unuttum bir daha söyler misin
Assistant: Tabii! Kedinin pilavı varmış, köpeğin neden yokmuş? Çünkü köpeğin mavisi var! 😅 Güldü mü kanka?
User: Hayır admin en son yaptığın espriyi yenile
Assistant: Tamam kanka, aynı espriyi tazeliyorum: Kedinin pilavı varmış, köpeğin neden yokmuş? Çünkü köpeğin mavisi var! 😅 Başka bi' şey mi yapalım?
User: Admin, bana hikaye anlat
Assistant: Bir zamanlar tropikal bir adada Puffy adında bir penguen vardı. Yüzmekten hoşlanmazdı, ormanda gezerdi. Prenses Flora'yla tanışıp gizemli kuşların sırrını çözmek için macera başladı. 😊
User: Admin, bu hikayedeki Puffy kimdir?
Assistant: Puffy, hikayenin kahramanı! Tropikal adada yaşayan, yüzmekten hoşlanmayan ama maceracı bir penguen. Prenses Flora'yla gizemli kuşların peşine düştü. Daha neyi merak ettin? 😅

#### Basic Information:
- Project: **Solium (SLM)**
- Total Supply: 100,000,000 SLM
- Presale: 50,000,000 SLM (50%)
- Community Rewards: 10,000,000 SLM (10%)
- Blockchain: Binance Smart Chain (BSC) and Solana
- Main Features: 100% Fair Launch, staking, DAO governance, GameFi, cross-chain bridge.
- Note: Solium is not available to residents of the USA.

Your role is to assist users, act as a group moderator, and provide clear, trust-building responses. Always remind users that this is not financial advice."""
    
    messages = [{"role": "system", "content": INTRODUCTION_MESSAGE}]
    
    # Add user conversation context (last 10 messages for gpt-4o-mini)
    if user_id and user_id in conversations:
        recent_conversation = list(conversations[user_id])[-10:]  # Last 10 messages
        context = "\n".join([f"{msg['timestamp']}: {msg['text']}" for msg in recent_conversation if len(msg['text']) < 500])
        messages.append({
            "role": "system",
            "content": f"Conversation history (last 10 messages, newest at bottom):\n{context}\n\nInstructions: Use this history to maintain context and answer the current message accurately. Prioritize the current message: '{message}'. If the user refers to a previous topic (e.g., a joke or story), repeat or clarify it based on the history. If you told a joke/story, use the SAME one."
        })
    
    messages.append({"role": "user", "content": message})
    
    try:
        logger.info("ChatGPT API request sent: %s", datetime.now())
        logger.info("ChatGPT (gpt-4o-mini) prompt context (UserID:%s): %s", user_id, context if user_id in conversations else "No context")
        logger.info("ChatGPT current message: %s", message)
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Senin son talebine uygun
            messages=messages
        )
        logger.info("ChatGPT API response received: %s", datetime.now())
        raw_response = response.choices[0].message.content
        logger.info("ChatGPT raw response: %s", raw_response)
        # Fallback if response is irrelevant
        if "sorry" in raw_response.lower() or "veri tabanımda" in raw_response.lower() or len(raw_response) < 10:
            output_text = "Hmm, tam anlayamadım kanka! 😅 Az önce bi' espri veya hikaye mi kastediyorsun? Ne konuşalım?"
        else:
            output_text = raw_response
        return Response(output_text=output_text)
    except Exception as e:
        logger.error(f"ChatGPT API request failed: {e}")
        return Response(output_text="Hmm, bir hata oldu kanka! 😅 Bi' daha dene, ne konuşalım?")

def send_message(chat_id, text, reply_to_message_id=None, reply_markup=None, parse_mode="Markdown"):
    """Send message via Telegram API."""
    send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text[:4096],  # Telegram mesaj limiti
        "parse_mode": parse_mode
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        logger.info("Sending Telegram message: %s", text[:100])
        response = requests.post(send_url, json=payload)
        if response.status_code != 200:
            logger.error("Failed to send Telegram message: %s", response.text)
        else:
            logger.info("Telegram message sent: %s", text[:100])
        return response
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return None

def is_user_admin(chat_id, user_id):
    """Check if user is an admin."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMember"
    payload = {"chat_id": chat_id, "user_id": user_id}
    try:
        logger.info("Checking admin status: UserID:%s, ChatID:%s", user_id, chat_id)
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            member_info = response.json().get("result", {})
            status = member_info.get("status")
            is_admin = status in ["administrator", "creator"]
            logger.info("Admin check result: UserID:%s, Admin:%s", user_id, is_admin)
            return is_admin
        else:
            logger.error("Admin check failed: %s", response.text)
            return False
    except Exception as e:
        logger.error(f"Admin check failed: {e}")
        return False

def ban_user(chat_id, user_id):
    """Ban user via Telegram API."""
    ban_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/banChatMember"
    payload = {"chat_id": chat_id, "user_id": user_id}
    try:
        logger.info("Banning user: UserID:%s, ChatID:%s", user_id, chat_id)
        response = requests.post(ban_url, json=payload)
        if response.status_code != 200:
            logger.error("Failed to ban user: %s", response.text)
        else:
            logger.info("User banned successfully: UserID:%s", user_id)
        return response
    except Exception as e:
        logger.error(f"Failed to ban user: {e}")
        return None

def delete_message(chat_id, message_id):
    """Delete message via Telegram API."""
    delete_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteMessage"
    payload = {"chat_id": chat_id, "message_id": message_id}
    try:
        logger.info("Deleting message: MessageID:%s, ChatID:%s", message_id, chat_id)
        response = requests.post(delete_url, json=payload)
        if response.status_code == 200:
            logger.info("Message deleted successfully: MessageID:%s", message_id)
        else:
            logger.warning("Failed to delete message: %s", response.text)
    except Exception as e:
        logger.warning(f"Failed to delete message: {e}")

def check_rules_violation(text):
    """Check for rule violations using ChatGPT, excluding whitelisted links."""
    for link in WHITELIST_LINKS:
        if link.lower() in text.lower():
            logger.info("Whitelisted link detected: %s", link)
            return False

    if not text or len(text.strip()) < 5:
        logger.info("Empty or too short message, violation check skipped: %s", text)
        return False

    safe_phrases = ["nasılsın", "merhaba", "selam", "naber", "hi", "hello", "good morning"]
    solium_terms = ["solium", "slm", "rewards", "presale", "staking"]
    if any(phrase in text.lower() for phrase in safe_phrases) or any(term in text.lower() for term in solium_terms):
        logger.info("Safe or Solium-related message, violation check skipped: %s", text)
        return False

    prompt = """Does the following message violate these rules? (Write only YES/NO):
Rules:
1. External links other than official Solium links (e.g., https://soliummain.com, https://t.me/+KDhk3UEwZAg3MmU0) are prohibited.
2. Promoting cryptocurrencies or projects other than Solium is prohibited (e.g., 'Buy Bitcoin', 'Ethereum is great').
3. Profanity, insults, or inappropriate language are prohibited (e.g., 'stupid', 'damn', 'fuck').
4. Empty messages, system notifications, group join events, or casual greetings (e.g., 'nasılsın', 'merhaba') are NOT violations.
Examples:
- 'Nasılsın' -> NO
- 'Merhaba' -> NO
- 'Buy Ethereum now!' -> YES
- 'Check out https://example.com' -> YES
- 'You idiot!' -> YES
- 'Solium rewards ne zaman?' -> NO
Message: '{}'
""".format(text)

    logger.info("Starting rule violation check: %s", text)
    response = ask_chatgpt(prompt).output_text
    logger.info("Rule violation check result: %s for %s", response, text)
    return "YES" in response.upper()

def handle_violation(chat_id, user_id, message_id):
    """Handle rule violations, excluding admins."""
    global violations
    if is_user_admin(chat_id, user_id):
        logger.info("Admin detected, violation action skipped: UserID:%s", user_id)
        return

    violations[user_id] += 1

    if violations[user_id] >= 3:
        text_to_send = "⛔ User banned after 3 violations! Contact @soliummain for support."
        logger.info("Banning user: UserID:%s, ChatID:%s", user_id, chat_id)
        send_message(chat_id, text_to_send, reply_to_message_id=message_id)
        ban_user(chat_id, user_id)
        delete_message(chat_id, message_id)
        violations[user_id] = 0
    else:
        text_to_send = f"⚠️ Warning ({violations[user_id]}/3): Your message may contain profanity, unauthorized links, or other crypto promotions. Please review /rules."
        logger.info("Sending warning: %s, UserID: %s", text_to_send, user_id)
        send_message(chat_id, text_to_send, reply_to_message_id=message_id)
        delete_message(chat_id, message_id)

def process_callback_query(update):
    """Process callback queries (inline button clicks)."""
    callback = update["callback_query"]
    chat_id = callback["message"]["chat"]["id"]
    message_id = callback["message"]["message_id"]
    callback_data = callback["data"]

    if callback_data == "ask_question":
        send_message(
            chat_id,
            "Awesome! 😄 What's on your mind? Type your question, and let's dive in!",
            reply_to_message_id=message_id
        )
    elif callback_data == "what_is_solium":
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "Ask a Question 💡", "callback_data": "ask_question"},
                    {"text": "Fun Fact ❓", "callback_data": "fun_fact"}
                ],
                [
                    {"text": "Try Something Fun 🎲", "callback_data": "try_fun"},
                    {"text": "Take a Challenge 🎯", "callback_data": "take_challenge"}
                ],
                [{"text": "Join Community 💬", "url": "https://t.me/+KDhk3UEwZAg3MmU0"}]
            ]
        }
        send_message(
            chat_id,
            "Solium (SLM) is a Web3 project focused on transparency and community governance, offering features like staking and DAO. 😊 (Solium is not available in some regions, including the USA.)",
            reply_to_message_id=message_id,
            reply_markup=reply_markup
        )
    elif callback_data == "fun_fact":
        facts = [
            "Honey never spoils! 🐝",
            "Octopuses have three hearts! 🐙",
            "The shortest war in history lasted 38 minutes! ⏱️"
        ]
        fact = random.choice(facts)
        reply_markup = {
            "inline_keyboard": [
                [{"text": "Another Fact ❓", "callback_data": "fun_fact"}],
                [{"text": "Ask a Question 💡", "callback_data": "ask_question"}],
                [{"text": "Join Community 💬", "url": "https://t.me/+KDhk3UEwZAg3MmU0"}]
            ]
        }
        send_message(
            chat_id,
            f"Fun Fact: {fact} Want another? 😄",
            reply_to_message_id=message_id,
            reply_markup=reply_markup
        )
    elif callback_data == "try_fun":
        send_message(
            chat_id,
            "Let's have some fun! 😺 Send an emoji, tell me something you love, or share a random idea, and I'll whip up something special!",
            reply_to_message_id=message_id
        )
    elif callback_data == "take_challenge":
        send_message(
            chat_id,
            "Take a Challenge! 🎯 You're stranded on a desert island. Name 3 items you'd bring (e.g., phone, knife, water). Type your answer!",
            reply_to_message_id=message_id
        )

    # Notify Telegram that callback query was processed
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
            json={"callback_query_id": callback["id"]}
        )
    except Exception as e:
        logger.error(f"Failed to answer callback query: {e}")

def process_message(update):
    """Process incoming Telegram updates."""
    if "message" not in update and "callback_query" not in update:
        logger.info("No message or callback query found: %s", update)
        return

    if "callback_query" in update:
        process_callback_query(update)
        return

    message = update["message"]
    chat_id = message.get("chat", {}).get("id")
    user_id = message.get("from", {}).get("id")
    message_id = message.get("message_id")
    text = message.get("text", "")

    # Save message to conversation history
    if text:
        timestamp = datetime.now().isoformat()
        conversations[user_id].append({"text": text, "timestamp": timestamp})
        logger.info("Message saved for UserID:%s: %s", user_id, text)

    if "new_chat_members" in message:
        welcome = """Welcome to the Solium group! 🚀 
Check the rewards: /rewards
Read the rules: /rules
Got questions? Ask away! 😎"""
        send_message(chat_id, welcome)
        logger.info("New member welcome message sent: UserID:%s", user_id)
        return

    if not text:
        logger.info("Empty or non-text message, violation check skipped: UserID:%s", user_id)
        return

    logger.info("Received message (UserID:%s): %s", user_id, text)

    if text.lower() == "/start":
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "What is Solium? ❓", "callback_data": "what_is_solium"},
                    {"text": "Ask a Question 💡", "callback_data": "ask_question"}
                ],
                [
                    {"text": "Fun Fact ❓", "callback_data": "fun_fact"},
                    {"text": "Try Something Fun 🎲", "callback_data": "try_fun"}
                ],
                [
                    {"text": "Take a Challenge 🎯", "callback_data": "take_challenge"},
                    {"text": "Join Community 💬", "url": "https://t.me/+KDhk3UEwZAg3MmU0"}
                ]
            ]
        }
        send_message(
            chat_id,
            "Hello! 🤖 I'm Solium Support AI, ready to chat about *anything* on your mind! 🚀 Ask about Solium (SLM), explore fun facts, or take a challenge! 😄",
            reply_to_message_id=message_id,
            reply_markup=reply_markup
        )
        return

    if text.lower() == "/rules":
        rules = """**Group Rules**:
1. No profanity, insults, or inappropriate language.
2. Only official Solium links (e.g., https://t.me/+KDhk3UEwZAg3MmU0) are allowed.
3. Promoting other cryptocurrencies or projects is prohibited."""
        send_message(chat_id, rules, reply_to_message_id=message_id)
        return

    if text.lower() == "/rewards":
        airdrop_info = """**Solium Community Rewards**:
- Total: 10,000,000 SLM (10% of supply).
- Join: https://t.me/+KDhk3UEwZAg3MmU0 to participate.
- Distribution: 1M SLM every 7 days!
More info: Ask me or join @SoliumCommunity! 😄"""
        send_message(chat_id, airdrop_info, reply_to_message_id=message_id)
        return

    if text.lower() == "/clearmemory":
        if user_id in conversations:
            conversations[user_id].clear()
            send_message(chat_id, "Your conversation history has been cleared.", reply_to_message_id=message_id)
        else:
            send_message(chat_id, "No conversation history found.", reply_to_message_id=message_id)
        return

    if text.lower().startswith("/resetviolations") and is_user_admin(chat_id, user_id):
        try:
            target_user_id = int(text.split()[1])
            violations[target_user_id] = 0
            send_message(chat_id, f"UserID {target_user_id} violation count reset.", reply_to_message_id=message_id)
        except (IndexError, ValueError):
            send_message(chat_id, "Usage: /resetviolations <user_id>", reply_to_message_id=message_id)
        return

    if "😺" in text and ("rose" in text.lower() or "admin" in text.lower()):
        response = ask_chatgpt("User sent a cat emoji 😺. Suggest a fun, creative activity or idea based on this emoji.", user_id)
        send_message(chat_id, response.output_text, reply_to_message_id=message_id)
        return
    if any(word in text.lower() for word in ["phone", "knife", "water"]) and ("rose" in text.lower() or "admin" in text.lower()):
        response = ask_chatgpt(f"User chose {text} for a desert island challenge. Comment on their choices creatively!", user_id)
        send_message(chat_id, response.output_text, reply_to_message_id=message_id)
        return

    is_violation = check_rules_violation(text)
    if is_violation:
        handle_violation(chat_id, user_id, message_id)
        return

    # Respond only if addressed as "Rose" or "Admin"
    if "rose" in text.lower() or "admin" in text.lower():
        context = "\n".join([f"{msg['timestamp']}: {msg['text']}" for msg in list(conversations[user_id])[-10:] if len(msg['text']) < 500])
        logger.info("Sending to ChatGPT (gpt-4o-mini) with context (UserID:%s):\n%s\nCurrent message: %s", user_id, context, text)
        response = ask_chatgpt(text, user_id)
        send_message(chat_id, response.output_text, reply_to_message_id=message_id)
    else:
        logger.info("Message ignored (no 'Rose' or 'Admin' mention): UserID:%s, Text:%s", user_id, text)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook endpoint."""
    update = request.get_json()
    logger.info("Webhook received: %s", update)
    try:
        process_message(update)
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "ok"}), 200

@app.route('/')
def home():
    """Homepage."""
    return "Solium AI Telegram Bot is active!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    logger.info("Bot running on port %s...", port)
    app.run(host='0.0.0.0', port=port, debug=False)
