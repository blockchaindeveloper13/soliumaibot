from flask import Flask
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.debug("Starting minimal application...")

app = Flask(__name__)

@app.route('/')
def home():
    logger.debug("Home endpoint accessed.")
    return "Minimal Solium AI Bot is active!"

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    logger.debug("Running on port %s...", port)
    app.run(host='0.0.0.0', port=port, debug=False)

logger.debug("Minimal application initialized.")
