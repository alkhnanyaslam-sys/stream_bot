import telebot
import os
import subprocess
import threading
import time
import logging

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
STREAM_URL = os.environ.get("STREAM_URL")
OUTPUT_URL = os.environ.get("OUTPUT_URL")

bot = telebot.TeleBot(BOT_TOKEN)

process = None
stop_flag = False


def run_stream():
    global process, stop_flag

    while not stop_flag:
        try:
            logging.info("🎬 Starting stream...")

            cmd = [
                "ffmpeg",
                "-re",
                "-stream_loop", "-1",
                "-i", STREAM_URL,

                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",

                "-f", "flv",
                OUTPUT_URL
            ]

            process = subprocess.Popen(cmd)
            process.wait()

            logging.warning("⚠️ Restarting stream in 5 sec...")
            time.sleep(5)

        except Exception as e:
            logging.error(f"Error: {e}")
            time.sleep(5)


@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "📡 Bot is running")

@bot.message_handler(commands=['stream'])
def stream(msg):
    global stop_flag
    stop_flag = False

    threading.Thread(target=run_stream).start()

    bot.reply_to(msg, "🚀 Stream started")

@bot.message_handler(commands=['stop'])
def stop(msg):
    global stop_flag, process

    stop_flag = True

    if process:
        process.terminate()
        process = None

    bot.reply_to(msg, "⛔ Stream stopped")

bot.polling(none_stop=True)
