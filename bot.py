import telebot
from telebot import types
import yt_dlp
import os
import tempfile
import threading
import glob
import time
import hashlib

TOKEN = '8516900372:AAHFtg-tsGO4QDlEa8SyW2hu4X3QIfuOlWg'
bot = telebot.TeleBot(TOKEN)

MAX_FILE_SIZE_MB = 50  # максимальный размер mp3
CACHE_DIR = os.path.join(tempfile.gettempdir(), "song_cache")

# создаём папку для кэша, если нет
os.makedirs(CACHE_DIR, exist_ok=True)

# Клавиатура с кнопкой Start
start_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
start_btn = types.KeyboardButton("Start")
start_kb.add(start_btn)

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(
        message.chat.id,
        "Привет! Нажми кнопку Start, чтобы продолжить 🎵",
        reply_markup=start_kb
    )

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text.lower() == "start":
        bot.send_message(message.chat.id, "Бот готов к работе! Напиши название песни.")
    else:
        threading.Thread(target=download_and_send, args=(message,)).start()

def download_and_send(message):
    query = message.text.strip()
    chat_id = message.chat.id
    bot.send_message(chat_id, f"🔎 Ищу песню: {query}")

    # создаём уникальное имя файла для кэша на основе запроса
    query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
    cached_file = os.path.join(CACHE_DIR, f"{query_hash}.mp3")

    # если песня уже есть в кэше, отправляем сразу
    if os.path.exists(cached_file):
        with open(cached_file, "rb") as audio:
            bot.send_audio(chat_id, audio, title=query)
        return

    # временный файл для скачивания
    temp_file = os.path.join(tempfile.gettempdir(), f"song_{chat_id}_{int(time.time())}.m4a")

    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "outtmpl": temp_file.replace(".m4a", ".%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "default_search": "ytsearch5",
        "ignoreerrors": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=True)

        # ищем mp3 файл
        mp3_files = glob.glob(temp_file.replace(".m4a", "*.mp3"))
        if not mp3_files:
            bot.send_message(chat_id, "Не удалось найти или скачать песню 😕")
            return

        file_path = mp3_files[0]

        # проверяем размер
        file_size_mb = os.path.getsize(file_path) / (1024*1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            bot.send_message(chat_id, f"Файл слишком большой ({file_size_mb:.1f} MB) 😕")
            os.remove(file_path)
            return

        # название песни
        if 'entries' in info and info['entries']:
            song_title = info['entries'][0].get('title', query)
        else:
            song_title = info.get('title', query)

        # копируем в кэш
        os.replace(file_path, cached_file)

        # отправляем пользователю
        with open(cached_file, "rb") as audio:
            bot.send_audio(chat_id, audio, title=song_title)

    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Ошибка при скачивании: {e}")

print("Бот запущен...")
bot.infinity_polling()
