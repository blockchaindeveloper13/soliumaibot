import tweepy
import os
import time
import random
import requests
import glob
import logging
import logging.handlers
from datetime import datetime, timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Logging setup with rotation
logging.basicConfig(
    filename="solium_bot.log",
    level=logging.INFO,
    format="%(asctime)s: %(levelname)s: %(message)s",
    handlers=[logging.handlers.RotatingFileHandler("solium_bot.log", maxBytes=10*1024*1024, backupCount=5)]
)

# Twitter API v1.1 Authentication
auth = tweepy.OAuth1UserHandler(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_SECRET_KEY"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)
api = tweepy.API(auth)

# Grok API Configuration
GROK_API_URL = "https://api.grok.ai/v1/generate"
GROK_HEADERS = {
    "Authorization": f"Bearer {os.getenv('GROK_API_KEY')}",
    "Content-Type": "application/json"
}

# Constants
HASHTAGS = "#Solium #Crypto #Web3 #Blockchain"  # ~28 chars
MAX_TWEET_LENGTH = 280
MAX_CONTENT_LENGTH = MAX_TWEET_LENGTH - len(HASHTAGS) - 2  # 1 space + 1 buffer
FALLBACK_TWEETS = [
    "Solium Coin ile Web3 dünyasına adım atın! 🚀 Stake yapın, kazanın. #Solium",
    "Merkeziyetsiz geleceğin parçası olun. Solium Coin DAO'ya katılın! 🌐 #Crypto",
    "Solium Coin: Şeffaflık ve topluluk odaklı bir kripto projesi. ⚡ #Blockchain",
    "Join Solium Coin’s Web3 revolution! Discover more at soliumcoin.com 💎 #Web3",
    "Stake with Solium Coin and be part of the future! 🚀 soliumcoin.com #Crypto"
]
BANNED_PHRASES = ["don't miss out", "get rich", "guaranteed", "profit", "moon", "pump"]
FALLBACK_TWEETS = [t for t in FALLBACK_TWEETS if is_safe_tweet(t)]  # Filter fallbacks

# Prompt variations for diversity
PROMPTS = [
    "Generate a tweet about Solium Coin's Web3 technology and community.",
    "Generate a tweet about how Solium Coin empowers users through staking.",
    "Generate a tweet about Solium Coin's decentralized vision."
]

def is_peak_time():
    """Check if current time is peak for crypto audience (UTC 14:00-23:00)."""
    utc_time = datetime.now(timezone.utc)
    return 14 <= utc_time.hour <= 23

def is_safe_tweet(content):
    """Check if content avoids banned phrases."""
    return not any(phrase in content.lower() for phrase in BANNED_PHRASES)

def grok_generate_content():
    """Generate Solium-focused tweet content using Grok API."""
    system_prompt = """
    You are a content generator for Solium Coin (SLM), a Web3 crypto project.
    - Target: Global crypto enthusiasts interested in Web3, staking, and DAOs.
    - Language: English (80%), Turkish (20%), occasionally Arabic phrases (e.g., 'انضم إلى سوليوم').
    - Tone: Professional, innovative, community-driven, engaging.
    - Length: Strictly under 180 characters (before hashtags).
    - Emojis: Use 1-2 max (🚀, 🌐, ⚡, 💎).
    - Call-to-Action: Include 'Join now', 'Learn more at soliumcoin.com', or 'Discover Solium'.
    - X Rules Compliance:
      - Avoid: Promises of profit, price predictions, FOMO phrases (e.g., 'Don't miss out!', 'Get rich quick'), or USA/Canada-specific warnings.
      - Focus: Highlight Solium's technology (Web3, staking, DAO), community, or vision.
      - Do not mention specific prices, returns, or unregulated financial advice.
    Example: 'Build the future with Solium Coin’s DAO! Join our community now. 🌐 soliumcoin.com #Solium #Crypto'
    """
    prompt = random.choice(PROMPTS)
    
    try:
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        
        response = session.post(
            GROK_API_URL,
            headers=GROK_HEADERS,
            json={
                "prompt": f"{system_prompt}\n\n{prompt}",
                "max_length": 180,
                "creativity": 0.7
            },
            timeout=15
        )
        response_data = response.json()
        if not isinstance(response_data, dict) or "text" not in response_data:
            raise ValueError("Unexpected Grok API response format")
        
        content = response_data["text"].strip()
        if not content or len(content) > 180 or not is_safe_tweet(content):
            raise ValueError("Invalid or unsafe content")
        
        logging.info(f"Grok generated: {content}")
        return content
    
    except Exception as e:
        logging.error(f"Grok error: {e}")
        return None

def post_tweet_with_retry():
    """Post tweet with error handling and rate limit awareness."""
    content = grok_generate_content() or random.choice(FALLBACK_TWEETS)
    tweet_text = f"{content[:MAX_CONTENT_LENGTH]} {HASHTAGS}"
    
    try:
        image_files = glob.glob("images/*.png")
        if image_files and random.random() < 0.7:
            media = api.media_upload(random.choice(image_files))
            api.update_status(status=tweet_text, media_ids=[media.media_id])
        else:
            api.update_status(tweet_text)
        logging.info(f"{datetime.now()}: Tweet posted: {tweet_text}")
        
    except tweepy.TweepyException as e:
        logging.error(f"Media or tweet error: {e}")
        api.update_status(tweet_text)  # Fallback to text-only tweet
    except tweepy.TooManyRequests as e:
        logging.warning(f"Rate limit exceeded: {e}")
        time.sleep(15 * 60)

def health_check():
    """Verify API connections before main loop."""
    try:
        api.verify_credentials()
        requests.get(GROK_API_URL, headers=GROK_HEADERS, timeout=5)
        return True
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return False

# Main Execution
if __name__ == "__main__":
    print("Solium Bot starting...")
    
    if not health_check():
        print("Critical APIs unavailable. Exiting.")
        exit(1)
    
    while True:
        post_tweet_with_retry()
        sleep_time = random.randint(21600, 28800) if is_peak_time() else random.randint(28800, 36000)  # 6-8h peak, 8-10h off-peak
        logging.info(f"Next tweet in {sleep_time//3600} hours...")
        time.sleep(sleep_time)
