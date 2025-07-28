import os
import asyncio
import logging
import tweepy
from aiohttp import web
from aiogram import Bot
from aiogram.types import InputMediaPhoto
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
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

async def notify_user_about_tweet(tweet):
    text = tweet.text

    media_group = []
    if hasattr(tweet, "attachments") and "media_keys" in tweet.attachments:
        media_keys = tweet.attachments["media_keys"]
        media = tweet.includes.get("media", [])

        for item in media:
            if item.media_key in media_keys and item.type == "photo":
                media_group.append(InputMediaPhoto(item.url))

    if media_group:
        await bot.send_media_group(TELEGRAM_USER_ID, media_group)
    await bot.send_message(TELEGRAM_USER_ID, text)

async def notify_startup():
    accounts = "\n".join(f"— {user.strip()}" for user in TWITTER_USERS)
    text = (
        "✅ <b>Бот успешно запущен</b>\n"
        "🔎 <b>Мониторинг аккаунтов:</b>\n"
        f"{accounts}"
    )
    await bot.send_message(TELEGRAM_USER_ID, text)
    
async def check_twitter_updates():
    while True:
        try:
            for username in TWITTER_USERS:
                user = twitter_client.get_user(username=username.strip())
                user_id = user.data.id

                tweets = twitter_client.get_users_tweets(
                    id=user_id,
                    max_results=5,
                    expansions="attachments.media_keys",
                    media_fields="url,type"
                )

                if tweets.data:
                    for tweet in reversed(tweets.data):
                        if last_tweet_ids.get(username) == tweet.id:
                            continue
                        last_tweet_ids[username] = tweet.id
                        await notify_user_about_tweet(tweet)

            await asyncio.sleep(1000)  # Проверять каждые 60 секунд
        except Exception as e:
            logging.error(f"Ошибка при получении твитов: {e}")
            await asyncio.sleep(1000)

# Простой веб-сервер для Render Web Service
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_app():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

# Главная асинхронная функция
async def main():
    await asyncio.gather(
        start_web_app(),         # Запускаем веб-сервер
        check_twitter_updates()  # Запускаем основную логику бота
    )

if __name__ == "__main__":
    asyncio.run(main())
