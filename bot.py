import tweepy
import requests
import os
import sqlite3
import time
from telegram import Bot, InputMediaPhoto
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID"))
TWITTER_BEARER = os.getenv("TWITTER_BEARER")
TWITTER_USERS = os.getenv("TWITTER_USERS", "").split(",")

client = tweepy.Client(bearer_token=TWITTER_BEARER, wait_on_rate_limit=True)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS tweets (id TEXT PRIMARY KEY)')
conn.commit()

def is_new_tweet(tweet_id):
    c.execute('SELECT 1 FROM tweets WHERE id=?', (tweet_id,))
    return c.fetchone() is None

def save_tweet_id(tweet_id):
    c.execute('INSERT INTO tweets (id) VALUES (?)', (tweet_id,))
    conn.commit()

def fetch_and_send_tweets():
    for username in TWITTER_USERS:
        try:
            user = client.get_user(username=username)
            user_id = user.data.id

            tweets = client.get_users_tweets(
                id=user_id,
                max_results=5,
                tweet_fields=['created_at', 'text', 'attachments'],
                expansions='attachments.media_keys',
                media_fields='url,type'
            )

            media_map = {}
            includes = tweets.includes
            if includes and "media" in includes:
                for media in includes["media"]:
                    media_map[media.media_key] = media

            for tweet in reversed(tweets.data or []):
                if not is_new_tweet(tweet.id):
                    continue

                text = tweet.text
                media_urls = []

                if tweet.attachments and 'media_keys' in tweet.attachments:
                    for key in tweet.attachments['media_keys']:
                        media = media_map.get(key)
                        if media and media.type == 'photo':
                            media_urls.append(media.url)

                if media_urls:
                    media_group = [InputMediaPhoto(url) for url in media_urls[:10]]
                    bot.send_media_group(chat_id=TELEGRAM_USER_ID, media=media_group)

                bot.send_message(chat_id=TELEGRAM_USER_ID, text=f"🐦 <b>@{username}</b>\n\n{text}", parse_mode=ParseMode.HTML)
                save_tweet_id(tweet.id)

        except Exception as e:
            print(f"[Ошибка] {username}: {e}")

if __name__ == '__main__':
    while True:
        fetch_and_send_tweets()
        time.sleep(120)
