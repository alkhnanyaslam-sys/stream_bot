import telebot
import os
import json
import subprocess
import threading
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

BOT_TOKEN = os.environ.get("(BOT_TOKEN)", "").strip()

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN مش موجود!")

bot = telebot.TeleBot(BOT_TOKEN)

DATA_FILE = "/tmp/stream_data.json"

STATIONS = {
    "1": {
        "name": "🕋 الحرم المكي المشرف",
        "urls": [
            "https://ws.stream.iqra.tv/hls/makkah/index.m3u8",
            "https://makkah.net/stream/makkah.m3u8",
            "https://cdn-streams.tv/haramain/makkah/hd/index.m3u8",
        ],
        "type": "video",
    },
    "2": {
        "name": "🕌 المسجد النبوي الشريف",
        "urls": [
            "https://ws.stream.iqra.tv/hls/madinah/index.m3u8",
            "https://madinah.net/stream/madinah.m3u8",
            "https://cdn-streams.tv/haramain/madinah/hd/index.m3u8",
        ],
        "type": "video",
    },
    "3": {
        "name": "📻 إذاعة القرآن الكريم - القاهرة",
        "urls": [
            "http://live.mp3quran.net:9722/",
            "http://live.mp3quran.net:9718/",
            "http://live.mp3quran.net:9714/",
        ],
        "type": "audio",
    },
}


def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {
            "admins": [],
            "process_running": False,
            "current_station": "1",
            "rtmp_url": "",
            "stream_key": "",
        }


def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, ensure_ascii=False)


data = load_data()
stream_process = None
stream_lock = threading.Lock()


def is_owner(uid):
    return bool(data["admins"]) and data["admins"][0] == uid


def is_admin(uid):
    return uid in data["admins"]


def test_url(url, timeout=8):
    """اختبار الرابط قبل البث"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-i", url,
             "-select_streams", "a", "-show_entries",
             "stream=codec_name", "-of", "default=noprint_wrappers=1"],
            timeout=timeout,
            capture_output=True
        )
        return result.returncode == 0
    except Exception:
        return False


def get_working_url(station_id):
    """جيب أول رابط شغال"""
    station = STATIONS[station_id]
    for url in station["urls"]:
        logging.info(f"اختبار: {url}")
        if test_url(url):
            logging.info(f"✅ شغال: {url}")
            return url
        logging.info(f"❌ فاشل: {url}")
    return None


def build_ffmpeg_cmd(url, dest, station_type):
    if station_type == "video":
        return [
            "ffmpeg",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-i", url,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-b:v", "2000k",
            "-maxrate", "2500k",
            "-bufsize", "5000k",
            "-vf", "scale=1280:720",
            "-g", "60",
            "-c:a", "aac",
            "-b:a", "160k",
            "-ar", "44100",
            "-ac", "2",
            "-f", "flv",
            "-loglevel", "warning",
            dest,
        ]
    else:
        # صوت فقط - نعمل صورة سوداء
        return [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "color=c=black:size=1280x720:rate=25",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-i", url,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "stillimage",
            "-b:v", "300k",
            "-g", "50",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-ac", "2",
            "-f", "flv",
            "-loglevel", "warning",
            dest,
        ]


def stop_stream():
    global stream_process
    with stream_lock:
        if stream_process and stream_process.poll() is None:
            stream_process.terminate()
            try:
                stream_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                stream_process.kill()
        stream_process = None
    data["process_running"] = False
    save_data(data)


def start_stream(rtmp_url, stream_key, station_id):
    global stream_process
    stop_stream()

    dest = f"{rtmp_url}/{stream_key}"
    logging.info(f"🎯 الوجهة: {dest}")

    working_url = get_working_url(station_id)
    if not working_url:
        logging.error("❌ كل الروابط فاشلة!")
        return False, "كل الروابط فاشلة"

    station_type = STATIONS[station_id]["type"]
    cmd = build_ffmpeg_cmd(working_url, dest, station_type)

    logging.info(f"🚀 تشغيل ffmpeg...")

    with stream_lock:
        stream_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    data["process_running"] = True
    data["current_station"] = station_id
    data["rtmp_url"] = rtmp_url
    data["stream_key"] = stream_key
    save_data(data)
    return True, working_url


def watchdog():
    while True:
        time.sleep(20)
        if data.get("process_running"):
            with stream_lock:
                proc = stream_process
            if proc is None or proc.poll() is not None:
                logging.warning("⚠️ البث وقف - إعادة تشغيل...")
                rtmp = data.get("rtmp_url")
                key = data.get("stream_key")
                station = data.get("current_station", "1")
                if rtmp and key:
                    start_stream(rtmp, key, station)


threading.Thread(target=watchdog, daemon=True).start()


# ======= أوامر البوت =======

@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.from_user.id
    if not data["admins"]:
        data["admins"].append(uid)
        save_data(data)
        bot.reply_to(message,
            "👑 *أهلاً! أنت المالك الآن*\n\n"
            "للبدء:\n"
            "`/go 1 rtmp://LINK KEY`\n\n"
            "استخدم /help للأوامر",
            parse_mode="Markdown")
        return
    bot.reply_to(message,
        "🕌 *بوت البث المباشر*\n\n"
        "1️⃣ الحرم المكي\n"
        "2️⃣ المسجد النبوي\n"
        "3️⃣ إذاعة القرآن - القاهرة\n\n"
        "/help للأوامر",
        parse_mode="Markdown")


@bot.message_handler(commands=["help"])
def cmd_help(message):
    uid = message.from_user.id
    if is_admin(uid):
        text = (
            "🎛 *أوامر الأدمن:*\n\n"
            "▶️ `/go [رقم] [RTMP] [KEY]`\n"
            "مثال:\n"
            "`/go 1 rtmp://dc4.rtmp.t.me/live xxxx`\n\n"
            "⏹ `/stop` - إيقاف البث\n"
            "🔀 `/switch [رقم]` - تغيير المحطة\n"
            "📊 `/status` - حالة البث\n"
            "📻 `/stations` - المحطات\n"
            "👤 `/addadmin [ID]` - إضافة أدمن\n"
            "❌ `/removeadmin [ID]` - حذف أدمن\n"
            "👥 `/admins` - قائمة الأدمنز"
        )
    else:
        text = (
            "🕌 *الأوامر:*\n\n"
            "📊 `/status` - حالة البث\n"
            "📻 `/stations` - المحطات"
        )
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=["go"])
def cmd_go(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ مش عندك صلاحية")
        return

    parts = message.text.split()
    if len(parts) < 4:
        bot.reply_to(message,
            "❌ *الاستخدام:*\n"
            "`/go [رقم] [RTMP] [KEY]`\n\n"
            "مثال:\n"
            "`/go 1 rtmp://dc4.rtmp.t.me/live مفتاح`",
            parse_mode="Markdown")
        return

    station_id = parts[1]
    rtmp_url = parts[2]
    stream_key = " ".join(parts[3:])

    if station_id not in STATIONS:
        bot.reply_to(message, f"❌ رقم غلط، اختار من 1 إلى {len(STATIONS)}")
        return

    station_name = STATIONS[station_id]["name"]
    msg = bot.reply_to(message, f"⏳ جاري اختبار الروابط وبدء البث...\n📺 {station_name}")

    success, result = start_stream(rtmp_url, stream_key, station_id)

    if success:
        time.sleep(5)
        running = stream_process and stream_process.poll() is None
        if running:
            bot.edit_message_text(
                f"✅ *البث شغال!*\n\n"
                f"📺 {station_name}\n"
                f"🔗 الرابط: `{result}`\n"
                f"🛡 المراقبة: مفعّلة",
                msg.chat.id, msg.message_id,
                parse_mode="Markdown")
        else:
            bot.edit_message_text(
                "⚠️ البث بدأ لكن وقف فجأة\n"
                "🔄 الـ Watchdog هيعيد التشغيل تلقائياً",
                msg.chat.id, msg.message_id)
    else:
        bot.edit_message_text(
            f"❌ فشل البث!\n"
            f"السبب: {result}\n\n"
            "جرب محطة تانية أو تأكد من الـ RTMP",
            msg.chat.id, msg.message_id)


@bot.message_handler(commands=["stop"])
def cmd_stop(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ مش عندك صلاحية")
        return
    if not data.get("process_running"):
        bot.reply_to(message, "⚠️ البث متوقف بالفعل")
        return
    stop_stream()
    bot.reply_to(message, "⏹ *تم إيقاف البث*", parse_mode="Markdown")


@bot.message_handler(commands=["switch"])
def cmd_switch(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ مش عندك صلاحية")
        return

    parts = message.text.split()
    if len(parts) < 2 or parts[1] not in STATIONS:
        bot.reply_to(message, f"❌ استخدم: `/switch [1-{len(STATIONS)}]`", parse_mode="Markdown")
        return

    station_id = parts[1]
    rtmp = data.get("rtmp_url")
    key = data.get("stream_key")

    if not rtmp or not key:
        bot.reply_to(message, "❌ استخدم /go الأول")
        return

    station_name = STATIONS[station_id]["name"]
    bot.reply_to(message, f"🔀 جاري التبديل إلى:\n{station_name}")
    success, result = start_stream(rtmp, key, station_id)

    if success:
        time.sleep(4)
        bot.reply_to(message, f"✅ تم التبديل إلى:\n{station_name}")
    else:
        bot.reply_to(message, f"❌ فشل: {result}")


@bot.message_handler(commands=["status"])
def cmd_status(message):
    if data.get("process_running"):
        sid = data.get("current_station", "1")
        name = STATIONS.get(sid, {}).get("name", "غير معروف")
        running = stream_process and stream_process.poll() is None
        icon = "🟢" if running else "🟡"
        status = "شغال" if running else "جاري إعادة التشغيل..."
        text = (
            f"{icon} *البث: {status}*\n\n"
            f"📺 {name}\n"
            f"🛡 المراقبة: مفعّلة"
        )
    else:
        text = (
            "🔴 *البث متوقف*\n\n"
            "للبدء:\n`/go [رقم] [RTMP] [KEY]`"
        )
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=["stations"])
def cmd_stations(message):
    text = "📺 *المحطات:*\n\n"
    for k, s in STATIONS.items():
        cur = "🔴" if k == data.get("current_station") and data.get("process_running") else "⚪"
        text += f"{cur} {k}. {s['name']}\n"
    text += "\nللبدء: `/go [رقم] [RTMP] [KEY]`"
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=["addadmin"])
def cmd_addadmin(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ المالك بس")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ `/addadmin [ID]`", parse_mode="Markdown")
        return
    try:
        new_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "❌ ID لازم يكون رقم")
        return
    if new_id in data["admins"]:
        bot.reply_to(message, "⚠️ موجود بالفعل")
        return
    data["admins"].append(new_id)
    save_data(data)
    bot.reply_to(message, f"✅ تم إضافة `{new_id}`", parse_mode="Markdown")


@bot.message_handler(commands=["removeadmin"])
def cmd_removeadmin(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ المالك بس")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ `/removeadmin [ID]`", parse_mode="Markdown")
        return
    try:
        rid = int(parts[1])
    except ValueError:
        bot.reply_to(message, "❌ ID لازم يكون رقم")
        return
    if rid == data["admins"][0]:
        bot.reply_to(message, "❌ مينفعش تحذف المالك")
        return
    if rid not in data["admins"]:
        bot.reply_to(message, "⚠️ مش موجود")
        return
    data["admins"].remove(rid)
    save_data(data)
    bot.reply_to(message, f"✅ تم حذف `{rid}`", parse_mode="Markdown")


@bot.message_handler(commands=["admins"])
def cmd_admins(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ مش عندك صلاحية")
        return
    if not data["admins"]:
        bot.reply_to(message, "مفيش أدمنز")
        return
    text = "👥 *الأدمنز:*\n\n"
    for i, aid in enumerate(data["admins"]):
        role = "👑 مالك" if i == 0 else "🛡 أدمن"
        text += f"{role}: `{aid}`\n"
    bot.reply_to(message, text, parse_mode="Markdown")


if __name__ == "__main__":
    logging.info("✅ البوت شغال...")
    if data.get("process_running") and data.get("rtmp_url") and data.get("stream_key"):
        logging.info("🔄 إعادة تشغيل البث...")
        start_stream(data["rtmp_url"], data["stream_key"], data.get("current_station", "1"))
    bot.infinity_polling(timeout=60, long_polling_timeout=30)
