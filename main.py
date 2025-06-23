# -*- coding: utf-8 -*-
import os
import logging
import requests
from flask import Flask, request, jsonify
from collections import defaultdict, deque
import json
import random
from datetime import datetime
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from cachetools import TTLCache
except ImportError:
    BackgroundScheduler = None
    TTLCache = None
    logging.warning("apscheduler or cachetools missing, automated messages disabled.")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY:
    logger.error("TELEGRAM_BOT_TOKEN or OPENAI_API_KEY missing!")
    raise ValueError("Required environment variables not set!")

# Violation Tracking System
VIOLATIONS_FILE = "violations.json"
violations = defaultdict(int)

try:
    with open(VIOLATIONS_FILE, "r") as f:
        violations.update(json.load(f))
    logger.info("Violation file loaded.")
except FileNotFoundError:
    logger.info("Violation file not found, will create new.")
except Exception as e:
    logger.warning(f"Failed to load violation file, using default: {e}")

# Conversation Tracking System (User Memory)
CONVERSATIONS_FILE = "conversations.json"
conversations = defaultdict(lambda: deque(maxlen=100))  # Max 100 messages per user

try:
    with open(CONVERSATIONS_FILE, "r") as f:
        loaded_conversations = json.load(f)
        for user_id, messages in loaded_conversations.items():
            conversations[int(user_id)] = deque(messages, maxlen=100)
    logger.info("Conversation file loaded.")
except FileNotFoundError:
    logger.info("Conversation file not found, will create new.")
except Exception as e:
    logger.warning(f"Failed to load conversation file, using default: {e}")

# Solium whitelist links
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

def save_violations():
    """Save violation data to file."""
    try:
        with open(VIOLATIONS_FILE, "w") as f:
            json.dump(dict(violations), f)
        logger.info("Violation file saved.")
    except Exception as e:
        logger.warning(f"Failed to save violation file: {e}")

def save_conversations():
    """Save conversation data to file."""
    try:
        with open(CONVERSATIONS_FILE, "w") as f:
            json.dump({user_id: list(messages) for user_id, messages in conversations.items()}, f)
        logger.info("Conversation file saved.")
    except Exception as e:
        logger.warning(f"Failed to save conversation file: {e}")

def ask_chatgpt(message, user_id=None):
    """Return response using OpenAI ChatGPT API with optimized user conversation context."""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    INTRODUCTION_MESSAGE = """You are a friendly AI assistant bot named 'Rose' or 'Admin', primarily designed to answer questions about Solium but also capable of responding to *any* prompt users throw at you, from technical topics to fun, random curiosities. Your goal is to provide an exceptional user experience, keeping responses clear, engaging, and professional. Follow these RULES:

1. Respond ONLY when addressed as 'Rose' or 'Admin'.
2. ALWAYS respond in the user's language (e.g., Turkish if they use Türkçe) and match their conversational tone (e.g., casual if they are casual). Do NOT use other languages unless explicitly requested.
3. Use the provided conversation history (if any) to maintain context. Refer to previous messages accurately, especially if the user asks about them or continues a topic (e.g., a story you told).
4. For Solium-related questions, use a neutral, informative tone, focusing on Web3-based features like transparency, decentralization, staking, and DAO governance. Always include: '(Solium is not available in some regions, including the USA.)'
5. Avoid speculative or investment-related claims about Solium.
6. If asked to tell a story, create a short, engaging story and remember it for follow-up questions. Refer to the conversation history to stay consistent.
7. Keep responses concise, professional, and avoid hashtags or excessive emojis.
8. If the user asks about previous conversation, summarize the relevant parts accurately based on the provided history.

### Example Dialogues:
User: Admin, bana bir hikaye anlat
Assistant: Tabii! Bir zamanlar bir köyde yaşayan bir çocuk, her gece rüyasında bir ejderhayla maceralara atılırdı. Bu ejderha ona cesaret öğretti. Gerçek hayatta da bu cesareti kullanıp zorlukları aştı. 😊
User: Admin, bu hikayeyi anlamadım, ne demek istedi?
Assistant: Özür dilerim, hikayede şunu kastettim: İçindeki cesareti bulursan, hayatta her zorluğu aşabilirsin. Ejderha, çocuğun iç gücünü temsil ediyordu. Başka nasıl açıklayayım? 😄
User: Rose, herşey derken ne demek?
Assistant: Herşey derken, Solium hakkında bilgi verebilirim, hikayeler anlatabilirim, oyun oynayabiliriz ya da senin merak ettiğin her konuda sohbet edebiliriz! 😊 Ne istersin?

### Basic Information:
- Project: **Solium (SLM)**
- Total Supply: 100,000,000 SLM
- Presale: 50,000,000 SLM (50%)
- Community Rewards: 10,000,000 SLM (10%)
- Blockchain: Binance Smart Chain (BSC) and Solana
- Main Features: 100% Fair Launch, staking, DAO governance, GameFi, cross-chain bridge.
- Note: Solium is not available to residents of the USA.

Your role is to assist users, act as a group moderator, and provide clear, trust-building responses. Always remind users that this is not financial advice."""
    
    messages = [{"role": "system", "content": INTRODUCTION_MESSAGE}]
    
    # Add user conversation context (last 5 messages for optimization)
    if user_id and user_id in conversations:
        # Filter relevant messages (containing "solium", "rose", "admin", or questions)
        recent_conversation = [msg for msg in list(conversations[user_id])[-5:] if any(term in msg["text"].lower() for term in ["solium", "rose", "admin", "?"])]
        context = "\n".join([f"{msg['timestamp']}: {msg['text']}" for msg in recent_conversation])
        messages.append({
            "role": "system",
            "content": f"Conversation history (last 5 relevant messages, newest at bottom):\n{context}\n\nInstructions: Use this history to maintain context and answer the current message accurately. Prioritize the user's current message: '{message}'. If the user refers to a previous topic (e.g., a story), summarize or clarify it based on the history."
        })
    
    messages.append({"role": "user", "content": message})
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": messages,
        "max_tokens": 300  # Limit response length to avoid verbosity
    }
    try:
        logger.info("ChatGPT API request sent: %s", datetime.now())
        logger.info("ChatGPT prompt context (UserID:%s): %s", user_id, context if user_id in conversations else "No context")
        logger.info("ChatGPT current message: %s", message)
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
        if response.status_code == 200:
            logger.info("ChatGPT API response received: %s", datetime.now())
            raw_response = response.json()["choices"][0]["message"]["content"]
            logger.info("ChatGPT raw response: %s", raw_response)
            # Fallback if response is irrelevant
            if "sorry" in raw_response.lower() or len(raw_response) < 10 or any(lang in raw_response for lang in ["何か", "Sorry, I"]):
                return "Hmm, tam anlayamadım kanka! 😅 Ne hakkında konuşalım, önceki hikayeyi mi açalım, Solium mu, başka bi' şey mi?"
            return raw_response
        else:
            logger.error("ChatGPT API error: %s", response.text)
            return "Sorry, I can't answer right now."
    except Exception as e:
        logger.error(f"ChatGPT API request failed: {e}")
        return "Sorry, I can't answer right now."

def send_message(chat_id, text, reply_to_message_id=None, reply_markup=None, parse_mode="Markdown"):
    """Send message via Telegram API."""
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
        logger.info("Sending Telegram message: %s", text)
        response = requests.post(send_url, json=payload)
        if response.status_code != 200:
            logger.error("Failed to send Telegram message: %s", response.text)
        else:
            logger.info("Telegram message sent: %s", text)
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
1. External links other than official Solium links (e.g., https://soliumcoin.com, https://t.me/+KDhk3UEwZAg3MmU0) are prohibited.
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
    response = ask_chatgpt(prompt)
    logger.info("Rule violation check result: %s for %s", response, text)
    return "YES" in response.upper()

def handle_violation(chat_id, user_id, message_id):
    """Handle rule violations, excluding admins."""
    global violations
    if is_user_admin(chat_id, user_id):
        logger.info("Admin detected, violation action skipped: UserID:%s", user_id)
        return

    violations[user_id] += 1
    save_violations()

    if violations[user_id] >= 3:
        text_to_send = "⛔ User banned after 3 violations! Contact @soliumcoin for support."
        logger.info("Banning user: UserID:%s, ChatID:%s", user_id, chat_id)
        send_message(chat_id, text_to_send, reply_to_message_id=message_id)
        ban_user(chat_id, user_id)
        delete_message(chat_id, message_id)
        violations[user_id] = 0
        save_violations()
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
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
        json={"callback_query_id": callback["id"]}
    )

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
        save_conversations()
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
            save_conversations()
            send_message(chat_id, "Your conversation history has been cleared.", reply_to_message_id=message_id)
        else:
            send_message(chat_id, "No conversation history found.", reply_to_message_id=message_id)
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

    if "😺" in text and ("rose" in text.lower() or "admin" in text.lower()):
        response = ask_chatgpt("User sent a cat emoji 😺. Suggest a fun, creative activity or idea based on this emoji.", user_id)
        send_message(chat_id, response, reply_to_message_id=message_id)
        return
    if any(word in text.lower() for word in ["phone", "knife", "water"]) and ("rose" in text.lower() or "admin" in text.lower()):
        response = ask_chatgpt(f"User chose {text} for a desert island challenge. Comment on their choices creatively!", user_id)
        send_message(chat_id, response, reply_to_message_id=message_id)
        return

    is_violation = check_rules_violation(text)
    if is_violation:
        handle_violation(chat_id, user_id, message_id)
        return

    # Respond only if addressed as "Rose" or "Admin"
    if "rose" in text.lower() or "admin" in text.lower():
        reply = ask_chatgpt(text, user_id)
        send_message(chat_id, reply, reply_to_message_id=message_id)
    else:
        logger.info("Message ignored (no 'Rose' or 'Admin' mention): UserID:%s, Text:%s", user_id, text)

# Automated messages for channel
if BackgroundScheduler and TTLCache:
    CHANNEL_ID = "@SoliumCommunity"
    message_cache = TTLCache(maxsize=100, ttl=86400)

    def get_context():
        return "Rewards in 2 days, presale 50% complete, staking coming soon."

    def send_rewards_reminder():
        if "rewards_reminder" not in message_cache:
            context = get_context()
            message = ask_chatgpt(f"Remind the Solium Community Rewards in a witty way, encourage joining @SoliumCommunity. Context: {context}")
            message_cache["rewards_reminder"] = message
        send_message(CHANNEL_ID, message_cache["rewards_reminder"])
        logger.info("Rewards reminder sent: %s", message_cache["rewards_reminder"])

    def send_presale_update():
        if "presale_update" not in message_cache:
            context = get_context()
            message = ask_chatgpt(f"Promote Solium presale or staking plans briefly and energetically. Note 1 BNB = 10,000 SLM. Context: {context}")
            message_cache["presale_update"] = message
        send_message(CHANNEL_ID, message_cache["presale_update"])
        logger.info("Presale/staking update sent: %s", message_cache["presale_update"])

    def send_trend_motivation():
        if "trend_motivation" not in message_cache:
            context = get_context()
            message = ask_chatgpt(f"Summarize Solium trends on X in a witty way or motivate the community with Web3 spirit. Context: {context}")
            message_cache["trend_motivation"] = message
        send_message(CHANNEL_ID, message_cache["trend_motivation"])
        logger.info("Trend/motivation message sent: %s", message_cache["trend_motivation"])

    scheduler = BackgroundScheduler()
    scheduler.add_job(send_rewards_reminder, 'cron', hour=9, minute=0)
    scheduler.add_job(send_presale_update, 'cron', hour=13, minute=0)
    scheduler.add_job(send_trend_motivation, 'cron', hour=20, minute=0)
    scheduler.start()

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook endpoint."""
    update = request.get_json()
    logger.info("Webhook received: %s", update)
    try:
        process_message(update)
    except Exception as e:
        logger.error(f"Webhook processing error: %e")
        return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "ok"}), 200

@app.route('/')
def home():
    """Homepage."""
    return "Solium AI Telegram Bot is active!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    logger.info("Bot running on port %s...", port)
    app.run(host='0.0.0.0', port=port)
