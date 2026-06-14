import telebot
import os
import subprocess
import threading
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# 🔑 التوكن من البيئة
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN مش موجود!")

bot = telebot.TeleBot(BOT_TOKEN)

# 🎬 رابط البث (حطه من عندك)
STREAM_URL = os.environ.get("STREAM_URL", "").strip()

# 🎯 أمر بدء البث
@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "📡 البوت شغال\nاستخدم /stream لبدء البث")

# ▶️ تشغيل البث
@bot.message_handler(commands=['stream'])
def stream(msg):
    if not STREAM_URL:
        bot.reply_to(msg, "❌ STREAM_URL مش متظبط في المتغيرات")
        return

    bot.reply_to(msg, "🚀 جاري تشغيل البث...")

    thread = threading.Thread(target=run_stream)
    thread.start()

# 🔥 تشغيل ffmpeg
def run_stream():
    while True:
        try:
            logging.info("Starting stream...")

            cmd = [
                "ffmpeg",
                
                # 📥 إدخال
                "-re",
                "-i", STREAM_URL,

                # 🎧 صوت + 🎥 صورة (حل مشاكل الشائع)
                "-c:v", "copy",
                "-c:a", "aac",

                # 🔁 إعادة ترميز لو فيه مشاكل توافق
                "-f", "flv",

                # 📡 output (حطه لو عندك RTMP)
                os.environ.get("OUTPUT_URL", "")
            ]

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.wait()

            logging.info("Stream stopped, restarting in 5 sec...")
            time.sleep(5)

        except Exception as e:
            logging.error(f"Error: {e}")
            time.sleep(5)

# ▶️ تشغيل البوت
bot.polling(none_stop=True)
