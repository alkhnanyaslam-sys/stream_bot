import telebot
import os
import subprocess
import threading
import time
import logging

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

stop_all = False
processes = []


# =========================
# 🎯 قائمة القنوات
# =========================
CHANNELS = [
    {
        "name": "channel1",
        "input": os.environ.get("STREAM_URL_1"),
        "output": os.environ.get("OUTPUT_URL_1")
    },
    {
        "name": "channel2",
        "input": os.environ.get("STREAM_URL_2"),
        "output": os.environ.get("OUTPUT_URL_2")
    }
]


# =========================
# ▶️ تشغيل قناة واحدة
# =========================
def run_stream(channel):
    global stop_all

    while not stop_all:
        try:
            logging.info(f"🎬 Starting {channel['name']}")

            cmd = [
                "ffmpeg",
                "-re",
                "-stream_loop", "-1",
                "-i", channel["input"],

                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",

                "-f", "flv",
                channel["output"]
            ]

            process = subprocess.Popen(cmd)
            processes.append(process)

            process.wait()

            logging.warning(f"⚠️ {channel['name']} crashed, restarting...")
            time.sleep(5)

        except Exception as e:
            logging.error(f"{channel['name']} error: {e}")
            time.sleep(5)


# =========================
# ▶️ تشغيل كل القنوات
# =========================
def start_all():
    threads = []

    for ch in CHANNELS:
        if not ch["input"] or not ch["output"]:
            continue

        t = threading.Thread(target=run_stream, args=(ch,))
        t.start()
        threads.append(t)

    return threads


# =========================
# 🤖 أوامر البوت
# =========================
@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "📡 Bot Ready")

@bot.message_handler(commands=['stream'])
def stream(msg):
    global stop_all

    stop_all = False

    start_all()

    bot.reply_to(msg, "🚀 All streams started")

@bot.message_handler(commands=['stop'])
def stop(msg):
    global stop_all, processes

    stop_all = True

    for p in processes:
        try:
            p.terminate()
        except:
            pass

    processes = []

    bot.reply_to(msg, "⛔ All streams stopped")

@bot.message_handler(commands=['status'])
def status(msg):
    bot.reply_to(msg, f"📊 Running channels: {len(CHANNELS)}")

# =========================
bot.polling(none_stop=True)
