import os
import json
import time
import logging
import requests
import schedule
from datetime import datetime
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class TwitchBot:
    def __init__(self):
        self.client_id = os.getenv("TWITCH_CLIENT_ID")
        self.client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        self.game_name = os.getenv("TWITCH_GAME_NAME", "Doomtrain")
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.cache_file = os.getenv("CACHE_FILE", "active_streams.json")
        self.poll_interval = int(os.getenv("POLL_INTERVAL_MINUTES", 5))
        
        self.access_token = None
        self.game_id = None
        self.active_streams = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
                return {}
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.active_streams, f)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def get_access_token(self):
        logger.info("Requesting new Twitch access token...")
        url = "https://id.twitch.tv/oauth2/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            logger.info("Access token acquired successfully.")
            return True
        else:
            logger.error(f"Failed to get access token: {response.status_code} - {response.text}")
            return False

    def get_game_id(self):
        if not self.access_token:
            if not self.get_access_token():
                return None
        
        logger.info(f"Resolving Game ID for '{self.game_name}'...")
        url = f"https://api.twitch.tv/helix/games?name={self.game_name}"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data["data"]:
                self.game_id = data["data"][0]["id"]
                logger.info(f"Found Game ID: {self.game_id}")
                return self.game_id
            else:
                logger.error(f"Game '{self.game_name}' not found on Twitch.")
                return None
        elif response.status_code == 401:
            if self.get_access_token():
                return self.get_game_id()
        else:
            logger.error(f"Failed to get game ID: {response.status_code} - {response.text}")
        return None

    def send_discord_notification(self, stream):
        if not self.discord_webhook_url:
            logger.warning("Discord Webhook URL not configured. Skipping notification.")
            return

        user_name = stream["user_name"]
        user_login = stream["user_login"]
        title = stream["title"]
        # Replace thumbnail placeholders
        thumbnail_url = stream["thumbnail_url"].replace("{width}", "1280").replace("{height}", "720")
        # Add timestamp to bypass discord cache if needed
        thumbnail_url += f"?t={int(time.time())}"
        
        stream_url = f"https://twitch.tv/{user_login}"
        
        embed = {
            "title": f"{user_name} is now live on Twitch!",
            "description": title,
            "url": stream_url,
            "color": 9442302, # Twitch Purple
            "fields": [
                {
                    "name": "Category",
                    "value": self.game_name,
                    "inline": True
                }
            ],
            "image": {
                "url": thumbnail_url
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        payload = {
            "embeds": [embed]
        }
        
        try:
            response = requests.post(self.discord_webhook_url, json=payload)
            if response.status_code in [200, 204]:
                logger.info(f"Notification sent for {user_name}")
            else:
                logger.error(f"Failed to send Discord notification: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")

    def poll_streams(self):
        if not self.game_id:
            if not self.get_game_id():
                return

        logger.info(f"Polling for live streams in category: {self.game_name}...")
        url = f"https://api.twitch.tv/helix/streams?game_id={self.game_id}"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                current_live_streams = data["data"]
                current_live_ids = [s["id"] for s in current_live_streams]
                
                # Check for new streams
                for stream in current_live_streams:
                    stream_id = stream["id"]
                    if stream_id not in self.active_streams:
                        logger.info(f"New stream detected: {stream['user_name']}")
                        self.send_discord_notification(stream)
                        self.active_streams[stream_id] = {
                            "user_name": stream["user_name"],
                            "started_at": stream["started_at"]
                        }
                
                # Remove streams that are no longer live
                ids_to_remove = []
                for cached_id in self.active_streams:
                    if cached_id not in current_live_ids:
                        ids_to_remove.append(cached_id)
                
                if ids_to_remove:
                    for rid in ids_to_remove:
                        logger.info(f"Stream ended: {self.active_streams[rid]['user_name']}")
                        del self.active_streams[rid]
                
                self._save_cache()
                
            elif response.status_code == 401:
                logger.info("Token expired. Refreshing...")
                if self.get_access_token():
                    self.poll_streams()
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Polling error: {e}")

    def run(self):
        logger.info(f"Starting Twitch Notifier for category '{self.game_name}'")
        logger.info(f"Poll interval: {self.poll_interval} minutes")
        
        # Initial poll
        self.poll_streams()
        
        # Schedule future polls
        schedule.every(self.poll_interval).minutes.do(self.poll_streams)
        
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    bot = TwitchBot()
    bot.run()
