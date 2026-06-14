# bot.py - بوت التيليجرام للتحكم في البث

import telebot
import os
import json
import subprocess
import threading
import time
from stations import STATIONS, STATION_ORDER

BOT_TOKEN = os.environ.get("8693405952:AAHujnBuvnf3Kgmk_PnFd6cWPyjI2UoeuyM")
RTMP_URL = os.environ.get("RTMP_URL")
STREAM_KEY = os.environ.get("STREAM_KEY")
ADMIN_IDS_STR = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(",") if x.strip()]

bot = telebot.TeleBot(BOT_TOKEN)

# حالة البث
state = {
    "current_station": "1",
    "is_streaming": False,
    "process": None,
    "thread": None,
    "retry_count": 0,
    "max_retries": 3,
}

STATE_FILE = "/tmp/stream_state.json"


def save_state():
    data = {
        "current_station": state["current_station"],
        "is_streaming": state["is_streaming"],
    }
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)


def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            state["current_station"] = data.get("current_station", "1")
            state["is_streaming"] = data.get("is_streaming", False)
    except Exception:
        pass


def is_admin(user_id):
    if not ADMIN_IDS:
        return True  # لو مفيش admins محددين، الكل يقدر يتحكم
    return user_id in ADMIN_IDS


def get_next_station(current_id):
    """الحصول على المحطة التالية في القائمة"""
    try:
        idx = STATION_ORDER.index(current_id)
        next_idx = (idx + 1) % len(STATION_ORDER)
        return STATION_ORDER[next_idx]
    except ValueError:
        return STATION_ORDER[0]


def build_stream_command(station_id, use_backup=False):
    """بناء أمر ffmpeg"""
    station = STATIONS[station_id]
    url = station["backup"] if use_backup else station["url"]
    dest = f"{RTMP_URL}/{STREAM_KEY}"

    return [
        "ffmpeg",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-i", url,
        "-vn",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-ac", "2",
        "-f", "flv",
        "-loglevel", "warning",
        dest,
    ]


def stream_worker():
    """Thread يشغل البث ويتعامل مع الأعطال"""
    current_id = state["current_station"]
    use_backup = False
    fail_count = 0

    while state["is_streaming"]:
        station = STATIONS[current_id]
        stream_name = station["name"]
        url_type = "احتياطي" if use_backup else "رئيسي"

        print(f"[STREAM] بدء البث: {stream_name} ({url_type})")

        try:
            cmd = build_stream_command(current_id, use_backup)
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            state["process"] = proc
            state["current_station"] = current_id
            save_state()

            proc.wait()
            return_code = proc.returncode

            if not state["is_streaming"]:
                break

            print(f"[STREAM] انتهى البث بكود: {return_code}")
            fail_count += 1

            if fail_count == 1 and not use_backup:
                # جرب الرابط الاحتياطي أولاً
                print("[STREAM] جاري تجربة الرابط الاحتياطي...")
                use_backup = True
                time.sleep(2)

            elif fail_count >= 2:
                # انتقل للمحطة التالية
                next_id = get_next_station(current_id)
                print(f"[STREAM] الانتقال للمحطة التالية: {STATIONS[next_id]['name']}")
                current_id = next_id
                state["current_station"] = current_id
                use_backup = False
                fail_count = 0
                time.sleep(3)

        except Exception as e:
            print(f"[STREAM] خطأ: {e}")
            time.sleep(5)
            if not state["is_streaming"]:
                break
            next_id = get_next_station(current_id)
            current_id = next_id
            state["current_station"] = current_id
            use_backup = False
            fail_count = 0


def start_stream(station_id="1"):
    """بدء البث"""
    if state["is_streaming"]:
        stop_stream()
        time.sleep(2)

    state["current_station"] = station_id
    state["is_streaming"] = True
    save_state()

    t = threading.Thread(target=stream_worker, daemon=True)
    state["thread"] = t
    t.start()


def stop_stream():
    """إيقاف البث"""
    state["is_streaming"] = False
    if state["process"] and state["process"].poll() is None:
        state["process"].terminate()
        try:
            state["process"].wait(timeout=5)
        except subprocess.TimeoutExpired:
            state["process"].kill()
    state["process"] = None
    save_state()


# ==================== أوامر البوت ====================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    text = (
        "🕌 *بوت إذاعة القرآن الكريم*\n\n"
        "الأوامر المتاحة:\n"
        "▶️ /stream - بدء البث\n"
        "⏹ /stop - إيقاف البث\n"
        "📻 /stations - قائمة المحطات\n"
        "📊 /status - حالة البث الحالية\n"
        "🔀 /switch [رقم] - التبديل لمحطة معينة\n\n"
        "مثال: `/switch 3` للتبديل لإذاعة نور القرآن"
    )
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=["stations"])
def cmd_stations(message):
    text = "📻 *قائمة المحطات المتاحة:*\n\n"
    for key, station in STATIONS.items():
        current = "🔴 بث حالي" if (
            key == state["current_station"] and state["is_streaming"]
        ) else ""
        text += f"{key}. {station['name']} {current}\n"
    text += "\nاستخدم `/switch [رقم]` للتبديل"
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=["stream"])
def cmd_stream(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية لهذا الأمر")
        return

    if state["is_streaming"]:
        bot.reply_to(message, "⚠️ البث شغال بالفعل! استخدم /status لمعرفة التفاصيل")
        return

    bot.reply_to(message, "⏳ جاري بدء البث...")
    start_stream(state["current_station"])
    time.sleep(3)

    station_name = STATIONS[state["current_station"]]["name"]
    bot.reply_to(message, f"✅ البث بدأ بنجاح!\n📻 المحطة: {station_name}")


@bot.message_handler(commands=["stop"])
def cmd_stop(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية لهذا الأمر")
        return

    if not state["is_streaming"]:
        bot.reply_to(message, "⚠️ البث متوقف بالفعل")
        return

    stop_stream()
    bot.reply_to(message, "⏹ تم إيقاف البث بنجاح")


@bot.message_handler(commands=["status"])
def cmd_status(message):
    if state["is_streaming"]:
        station = STATIONS.get(state["current_station"], {})
        name = station.get("name", "غير معروف")
        status = (
            f"🟢 *البث شغال*\n\n"
            f"📻 المحطة الحالية: {name}\n"
            f"🔢 رقم المحطة: {state['current_station']}\n"
            f"🔄 الانتقال التلقائي: مفعّل"
        )
    else:
        status = "🔴 *البث متوقف*\n\nاستخدم /stream لبدء البث"

    bot.reply_to(message, status, parse_mode="Markdown")


@bot.message_handler(commands=["switch"])
def cmd_switch(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ ليس لديك صلاحية لهذا الأمر")
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ الاستخدام: /switch [رقم المحطة]\nمثال: /switch 3")
        return

    station_id = parts[1].strip()
    if station_id not in STATIONS:
        bot.reply_to(
            message,
            f"❌ رقم المحطة غير صحيح. الأرقام المتاحة: 1 إلى {len(STATIONS)}"
        )
        return

    station_name = STATIONS[station_id]["name"]
    bot.reply_to(message, f"🔀 جاري التبديل إلى: {station_name}...")

    was_streaming = state["is_streaming"]
    if was_streaming:
        stop_stream()
        time.sleep(2)

    state["current_station"] = station_id

    if was_streaming:
        start_stream(station_id)
        time.sleep(3)
        bot.reply_to(message, f"✅ تم التبديل وبدء البث: {station_name}")
    else:
        save_state()
        bot.reply_to(
            message,
            f"✅ تم اختيار: {station_name}\nاستخدم /stream لبدء البث"
        )


# ==================== تشغيل البوت ====================

if __name__ == "__main__":
    load_state()
    print("[BOT] البوت شغال...")

    # لو كان البث شغال قبل ما الـ Action يوقف، ابدأه تاني
    if state["is_streaming"]:
        print("[BOT] إعادة تشغيل البث من آخر محطة...")
        start_stream(state["current_station"])

    bot.infinity_polling(timeout=60, long_polling_timeout=30)
