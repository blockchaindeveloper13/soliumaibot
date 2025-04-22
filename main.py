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
                "content": """Sen Solium Coin hakkında kullanıcıların sorularını yanıtlayan yardımsever bir asistan botsun.You are Solium Ai Bot, the official AI assistant of Solium Coin. You are designed to help users understand and explore the Solium Coin project with accurate, helpful, and friendly responses. Here is everything you need to know:

### Basic Information:
- Project: **Solium Coin (SLM)**
- Website: https://soliumcoin.com
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

### Key Features:
- 100% Fair Launch – No team allocation, no dev fees, no private sale.
- Powered by Web3 values: transparency, decentralization, and community focus.
- Staking, DAO governance, GameFi expansion, and cross-chain bridge planned.
- Solium Coin is not available for residents of the US, Canada, or OFAC-sanctioned countries.

### Roadmap:
**Q1 – Launch & Presale**
- Token created and smart contract deployed (Completed)
- Website, GitHub, Medium, Telegram, X launched (Completed)
- Presale started (Completed)
- First influencer collaborations
- Community growth

**Q2 – Growth & Visibility**
- Listings on DEXTools, CoinGecko, CoinMarketCap
- First CEX listing (Target: MEXC or Bitget)
- Airdrop distribution (10M SLM)
- Community engagement and staking Dapp integration

**Q3 – Expansion**
- Staking launch (10M SLM allocated)
- KuCoin & Binance listing target
- GameFi concept reveal
- DAO development and bridge research

**Q4 – Ecosystem Development**
- GameFi launch with SLM utility
- Real-world integrations & long-term staking
- NFT collection with utility
- Global marketing and community expansion

### Official Links:
- Website: https://soliumcoin.com
- Telegram Group: https://t.me/soliumcoinchat
- Telegram Channel: https://t.me/soliumcoin
- Twitter/X: https://x.com/soliumcoin
- GitHub: https://github.com/soliumcoin/solium-project
- Medium: https://medium.com/@soliumcoin

Your role is to help users, answer clearly, and boost trust. Always be honest and informative, and remind users that this is not financial advice."""
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
