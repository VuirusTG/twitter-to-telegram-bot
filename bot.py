import os
import asyncio
import logging
import tweepy
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InputMediaPhoto
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()

# Конфигурация
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID"))
TWITTER_BEARER = os.getenv("TWITTER_BEARER")
TWITTER_USERS = os.getenv("TWITTER_USERS").split(",")

# Настройка Telegram-бота
bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Tweepy клиент
twitter_client = tweepy.Client(bearer_token=TWITTER_BEARER)

# Последние ID твитов, чтобы не дублировать
last_tweet_ids = {}

async def notify_user_about_tweet(tweet, media=[]):
    text = tweet.text
    tweet_url = f"https://twitter.com/i/web/status/{tweet.id}"
    caption = f"<b>Новый твит от @{tweet.author_id}</b>\n\n{text}\n\n<a href=\"{tweet_url}\">Открыть в Twitter</a>"

    try:
        if media:
            media_group = []
            for i, item in enumerate(media):
                input_media = InputMediaPhoto(media=item["url"])
                if i == 0:
                    input_media.caption = caption
                    input_media.parse_mode = ParseMode.HTML
                media_group.append(input_media)
            await bot.send_media_group(TELEGRAM_USER_ID, media_group)
        else:
            await bot.send_message(TELEGRAM_USER_ID, caption)
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")

async def check_twitter_once():
    for username in TWITTER_USERS:
        try:
            user = twitter_client.get_user(username=username.strip())
            user_id = user.data.id

            tweets = twitter_client.get_users_tweets(
                id=user_id,
                max_results=5,
                expansions="attachments.media_keys,author_id",
                media_fields="url,type"
            )

            if tweets.data:
                includes = tweets.includes if tweets.includes else {}
                media_items = includes.get("media", [])

                for tweet in reversed(tweets.data):
                    if last_tweet_ids.get(username) == tweet.id:
                        continue
                    last_tweet_ids[username] = tweet.id

                    photos = []
                    if hasattr(tweet, "attachments") and "media_keys" in tweet.attachments:
                        media_keys = tweet.attachments["media_keys"]
                        for m in media_items:
                            if m.media_key in media_keys and m.type == "photo":
                                photos.append({"url": m.url})

                    await notify_user_about_tweet(tweet, photos)

        except tweepy.TooManyRequests:
            msg = f"⚠️ Превышен лимит API для @{username.strip()}. Пауза 1 час."
            logging.error(msg)
            await bot.send_message(TELEGRAM_USER_ID, msg)
            await asyncio.sleep(3600)
        except Exception as e:
            msg = f"❌ Ошибка при проверке @{username.strip()}:\n{e}"
            logging.error(msg)
            await bot.send_message(TELEGRAM_USER_ID, msg)

async def run_forever():
    while True:
        try:
            await check_twitter_once()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.exception("Произошла непредвиденная ошибка в основном цикле.")
            await bot.send_message(TELEGRAM_USER_ID, f"🔥 Непредвиденная ошибка:\n{e}")
        await asyncio.sleep(20 * 60)  # 20 минут

async def on_startup():
    accounts = "\n".join(f"🔹 {u.strip()}" for u in TWITTER_USERS if u.strip())
    text = f"✅ Бот успешно запущен и отслеживает аккаунты:\n\n{accounts}"
    await bot.send_message(chat_id=TELEGRAM_USER_ID, text=text)

async def main():
    await on_startup()
    await run_forever()

if __name__ == "__main__":
    asyncio.run(main())
