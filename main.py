import tweepy
import os
import time
import random
import requests
from datetime import datetime

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
HASHTAGS = "#Solium #Crypto #Blockchain"  # ~30 chars
MAX_TWEET_LENGTH = 280
MAX_CONTENT_LENGTH = MAX_TWEET_LENGTH - len(HASHTAGS) - 1  # 1 space

# Fallback Messages (if Grok fails)
FALLBACK_TWEETS = [
    "Solium Coin ile Web3 dünyasına adım atın! 🚀 Stake yapın, kazanın. #Solium",
    "Merkeziyetsiz geleceğin parçası olun. Solium Coin DAO'ya katılın! 🌐 #Crypto",
    "Solium Coin: Şeffaflık ve topluluk odaklı bir kripto projesi. ⚡ #Blockchain"
]

def grok_generate_content():
    """Generate Solium-focused tweet content using Grok API."""
    system_prompt = """
    You are a content generator for Solium Coin (SLM), a Web3 project. Rules:
    - Language: Turkish or English (randomly choose).
    - Tone: Professional, engaging, and slightly technical.
    - Focus: Highlight Solium's Web3, staking, or DAO features.
    - Length: Strictly under 180 characters (before hashtags).
    - Use 1-2 emojis max (🚀, ⚡, 🌐).
    - Avoid: Price talk, investment advice, or USA/Canada warnings.
    Example: "Solium Coin ile merkeziyetsiz geleceği keşfedin! Stake ödüllerinden yararlanın. 🚀 #Solium"
    """
    
    prompt = "Generate a fresh tweet about Solium Coin's technology:"
    
    try:
        response = requests.post(
            GROK_API_URL,
            headers=GROK_HEADERS,
            json={
                "prompt": f"{system_prompt}\n\n{prompt}",
                "max_length": 180,
                "creativity": 0.7  # Balances creativity vs. safety
            },
            timeout=10
        )
        content = response.json().get("text", "").strip()
        
        # Quality control
        if not content or len(content) > 180:
            raise ValueError("Invalid content length")
            
        return content
    
    except Exception as e:
        print(f"Grok error: {e}")
        return None

def post_tweet_with_retry():
    """Post tweet with error handling and rate limit awareness."""
    content = grok_generate_content() or random.choice(FALLBACK_TWEETS)
    tweet_text = f"{content[:MAX_CONTENT_LENGTH]} {HASHTAGS}"
    
    try:
        # Tweet length double-check
        if len(tweet_text) > MAX_TWEET_LENGTH:
            tweet_text = tweet_text[:MAX_TWEET_LENGTH]
        
        api.update_status(tweet_text)
        print(f"{datetime.now()}: Tweet posted: {tweet_text[:50]}...")
        
    except tweepy.TooManyRequests as e:
        wait_time = 15 * 60  # 15 minutes
        print(f"Rate limit exceeded. Waiting {wait_time} sec... Error: {e}")
        time.sleep(wait_time)
        
    except tweepy.TweepyException as e:
        print(f"Twitter error: {e}")
        time.sleep(60)

def health_check():
    """Verify API connections before main loop."""
    try:
        # Test Twitter API
        api.verify_credentials()
        # Test Grok API (simple ping)
        requests.get(GROK_API_URL, headers=GROK_HEADERS, timeout=5)
        return True
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

# Main Execution
if __name__ == "__main__":
    print("Solium Bot starting...")
    
    if not health_check():
        print("Critical APIs unavailable. Exiting.")
        exit(1)
    
    while True:
        post_tweet_with_retry()
        
        # Dynamic sleep (1-2 hours to avoid patterns)
        sleep_time = random.randint(3600, 7200)
        print(f"Next tweet in {sleep_time//3600} hours...")
        time.sleep(sleep_time)
