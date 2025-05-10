import os
import logging
import requests
from flask import Flask, request, jsonify
from collections import defaultdict
import json

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ... (TELEGRAM_BOT_TOKEN ve OPENAI_API_KEY tanımları)

# İhlal Takip Sistemi
VIOLATIONS_FILE = "violations.json"
violations = defaultdict(int)

try:
    with open(VIOLATIONS_FILE, "r") as f:
        violations.update(json.load(f))
except FileNotFoundError:
    pass

def save_violations():
    with open(VIOLATIONS_FILE, "w") as f:
        json.dump(violations, f)


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

###Solium Coin (SLM) offers several key features and reasons for users to consider:

1. **100% Public Launch**: Solium Coin had a fair and transparent launch with no hidden wallets or early access, ensuring equal opportunities for all participants.

2. **Verified Smart Contracts**: The smart contracts of Solium Coin have been audited, providing transparency and security for users.

3. **BNB Chain Powered**: Solium Coin operates on the Binance Smart Chain (BSC), offering fast transactions, low fees, and a high level of security.

4. **Airdrop, Staking & Gaming**: Solium Coin is designed to reward its community members through airdrops, staking opportunities, and upcoming GameFi features.

5. **Web3 Ready**: Solium Coin is prepared for the Web3 ecosystem with multi-wallet integration, DEX compatibility, and a focus on decentralized applications.

These features make Solium Coin an attractive project for users looking to participate in a transparent, community-focused, and innovative cryptocurrency ecosystem.

Solium Coin is a groundbreaking cryptocurrency project with a mission to revolutionize the blockchain space by [Short description of the project's goal, for example: "empower decentralized finance with innovative solutions"]. It is supported by a dedicated team and is committed to advancing [Main objective, for example: "scalable blockchain technology"]. 

To get involved and be part of the future, you can join our Airdrop and Presale. Visit our website at https://soliumcoin.com to learn more about Solium Coin, our vision, and how you can participate in shaping the future of blockchain technology. 

Join the movement with #SoliumCoin and stay updated on the latest news in the crypto space. #Crypto

Solium Coin offers several key advantages that set it apart from other projects in the crypto space:

1. **Speed:** Solium Coin transactions are lightning-fast, thanks to the underlying technology of the Binance Smart Chain and Solana. This means you can quickly and efficiently send and receive funds without delays.

2. **Security:** With advanced encryption protocols in place, Solium Coin ensures that your funds are safe and secure. You can have peace of mind knowing that your assets are protected against potential threats.

3. **Scalability:** Solium Coin is built to scale, meaning it can handle a high volume of transactions and users without compromising speed or efficiency. This scalability makes it a robust platform for future growth.

4. **Community-Driven:** Solium Coin is backed by a passionate and growing community of crypto enthusiasts who are actively involved in shaping the project's development. By joining this community, you can engage with like-minded individuals and be part of the future of finance.

If you're interested in exploring the future of finance with Solium Coin, consider participating in the Airdrop and Presale to get involved early. You can join the community on Telegram at t.me/soliumcoinchat and learn more about the project at https://soliumcoin.com. #SoliumCoin #Crypto

It seems like there might be a confusion in the roadmap timeline you provided. As of my last update, the roadmap for Solium Coin was as follows:

**Q1 – Launch & Presale**
- Token created and smart contract deployed (Completed)
- Website, GitHub, Social Media platforms launched (Completed)
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

For the most up-to-date roadmap and information about Solium Coin, I recommend visiting the official website at [www.soliumcoin.com](https://soliumcoin.com) or joining the Telegram group at [t.me/soliumcoinchat](https://t.me/soliumcoinchat).

If you have any specific questions about Solium Coin, feel free to ask!

I'm glad to see your commitment to transparency and security in the Solium Coin project! Here are some key points that demonstrate the commitment to transparency in Solium Coin:

1. **Audited Smart Contracts**: Solium Coin's smart contracts on Binance Smart Chain (BSC) and Solana have been audited to ensure security and reliability. Users can verify the BSC Contract Address: 0x307a0dc0814CbD64E81a9BC8517441Ca657fB9c7

2. **Public GitHub Repository**: The project's code is publicly available on GitHub at https://github.com/soliumcoin/solium-project, allowing users to review and verify the codebase for transparency.

3. **No Team Allocation or Private Sale**: Solium Coin has no team allocation or private sale, ensuring that every token is earned through fair means. This aligns with the project's commitment to fairness and trust.
🚀🌟 Thank you for sharing the exciting news about the Solium Coin Airdrop and Presale! Here are some key details for everyone interested:

🎁 **Airdrop:** Participate in the Airdrop by joining the Solium Coin Telegram group at [t.me/soliumcoinchat](https://t.me/soliumcoinchat) and sharing your BSC address. You have the chance to win up to 1M $SLM every 7 days!

💰 **Presale:** Purchase $SLM with BNB (1 BNB = 10,000 $SLM) via MetaMask at [www.soliumcoin.com](www.soliumcoin.com). Top buyers stand a chance to win exciting prizes:
1️⃣ 1st: 1M $SLM
2️⃣ 2nd: 500K $SLM
3️⃣ 3rd: 100K $SLM
And more prizes for 4th to 10th place!

⏳ **Time Left:** Hurry! There are 21 days left to participate in the Presale and Airdrop. Don't miss out on this opportunity to be a part of the Solium Coin journey! 🌟🚀

#SoliumCoinAirdrop #SoliumCoinPresale

By providing access to audited smart contracts, a public code repository, and transparent token distribution, Solium Coin aims to build a community based on trust and openness. For more information on Solium Coin's transparency and security measures, you can visit their website at www.soliumcoin.com. #SoliumCoinTransparency 🛡️

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
# --- Mesaj işleme fonksiyonu ---
def process_message(update):
    if "message" not in update:
        logger.info("Mesaj bulunamadı: %s", update)
        return

    message = update["message"]
    chat_id = message.get("chat", {}).get("id")
    user_id = message.get("from", {}).get("id")  # Kullanıcı ID'sini ekledik
    text = message.get("text", "")
    message_id = message.get("message_id")  # Mesaj silme için

    logger.info("Gelen mesaj (UserID:%s): %s", user_id, text)

    # 1. Önce grup kural kontrolü yap
    is_violation = check_rules_violation(text)
    
    if is_violation:
        handle_violation(chat_id, user_id, message_id)
        return  # İhlal durumunda normal yanıt vermeyi atla
    
    # 2. Orijinal işlevselliği koru (ChatGPT yanıtı)
    reply = ask_chatgpt(text)
    send_message(chat_id, reply)

# --- Yardımcı Fonksiyonlar ---
def check_rules_violation(text):
    """ChatGPT ile kural ihlali kontrolü"""
    prompt = """Aşağıdaki mesaj bu kurallara aykırı mı? (Sadece EVET/HAYIR yaz):
    Kurallar:
    1. Küfür/hakaret yasak
    2. Spam/flood yasak
    3. Reklam yasak (dış linkler)
    4. NSFW içerik yasak
    Mesaj: '{}'""".format(text)
    
    response = ask_chatgpt(prompt)
    return "EVET" in response.upper()

def handle_violation(chat_id, user_id, message_id):
    """İhlal işleme mekanizması"""
    global violations
    
    # 1. İhlal sayacını güncelle
    violations[user_id] += 1
    save_violations()
    
    # 2. Uyarı mesajı gönder
    warn_msg = f"⚠️ Uyarı ({violations[user_id]}/3): Grup kurallarını ihlal ettiniz!"
    send_message(chat_id, warn_msg)
    
    # 3. Mesajı sil (bot adminse)
    try:
        delete_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteMessage"
        requests.post(delete_url, json={"chat_id": chat_id, "message_id": message_id})
    except Exception as e:
        logger.error("Mesaj silinemedi: %s", e)
    
    # 4. 3. ihlalde ban
    if violations[user_id] >= 3:
        send_message(chat_id, f"/ban {user_id}")  # Rose Bot komutu
        violations[user_id] = 0  # Sayaç sıfırla
        save_violations()

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
