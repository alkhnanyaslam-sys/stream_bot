import telebot
import os
import json
import subprocess
import threading
import time

BOT_TOKEN = os.environ.get("8693405952:AAHujnBuvnf3Kgmk_PnFd6cWPyjI2UoeuyM")
bot = telebot.TeleBot(BOT_TOKEN)

DATA_FILE = "/tmp/stream_data.json"

# ======= تحميل وحفظ البيانات =======
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {
            "admins": [],
            "streams": {},
            "process_running": False,
            "current_station": None,
        }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ======= البث =======
stream_process = None
stream_lock = threading.Lock()

STATIONS = {
    "1": {
        "name": "🕋 الحرم المكي المشرف",
        "url": "https://ws.stream.iqra.tv/hls/makkah/index.m3u8",
        "backup": "https://cdn-streams.tv/haramain/makkah/hd/index.m3u8",
    },
    "2": {
        "name": "🕌 المسجد النبوي الشريف",
        "url": "https://ws.stream.iqra.tv/hls/madinah/index.m3u8",
        "backup": "https://cdn-streams.tv/haramain/madinah/hd/index.m3u8",
    },
    "3": {
        "name": "📻 إذاعة القرآن الكريم - القاهرة",
        "url": "http://stream.radiotime.com/listen.stream?streamid=3538",
        "backup": "http://live.mp3quran.net:9722/",
    },
}

def is_owner(user_id):
    """أول أدمن في القائمة هو المالك"""
    return data["admins"] and data["admins"][0] == user_id

def is_admin(user_id):
    return user_id in data["admins"]

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

    station = STATIONS.get(station_id)
    if not station:
        return False

    url = station["url"]
    dest = f"{rtmp_url}/{stream_key}"

    # لو فيديو (الحرمين) هنحول مع فيديو، لو صوت بس نعمل صوت
    if station_id in ["1", "2"]:
        cmd = [
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
        # إذاعة صوت فقط - نعمل صورة ثابتة
        cmd = [
            "ffmpeg",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-loop", "1",
            "-i", "/tmp/quran_bg.jpg",
            "-i", url,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "stillimage",
            "-b:v", "500k",
            "-vf", "scale=1280:720",
            "-g", "60",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-ac", "2",
            "-shortest",
            "-f", "flv",
            "-loglevel", "warning",
            dest,
        ]

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
    return True

def watchdog():
    """مراقب يعيد تشغيل البث لو وقف"""
    while True:
        time.sleep(15)
        if data.get("process_running"):
            with stream_lock:
                proc = stream_process
            if proc is None or proc.poll() is not None:
                print("⚠️ البث وقف، إعادة تشغيل...")
                rtmp = data.get("rtmp_url")
                key = data.get("stream_key")
                station = data.get("current_station")
                if rtmp and key and station:
                    # جرب الرابط الاحتياطي
                    backup = STATIONS[station]["backup"]
                    STATIONS[station]["url"] = backup
                    start_stream(rtmp, key, station)

# شغّل الـ watchdog
t = threading.Thread(target=watchdog, daemon=True)
t.start()

# ======= صورة خلفية للإذاعة =======
def download_bg():
    try:
        subprocess.run([
            "wget", "-q", "-O", "/tmp/quran_bg.jpg",
            "https://i.imgur.com/JKaLvhZ.jpg"
        ], timeout=30)
    except Exception:
        # لو فشل التحميل، اعمل صورة بسيطة بـ ffmpeg
        subprocess.run([
            "ffmpeg", "-f", "lavfi",
            "-i", "color=c=black:size=1280x720:rate=1",
            "-frames:v", "1",
            "/tmp/quran_bg.jpg"
        ], capture_output=True)

download_bg()

# ======= أوامر البوت =======

@bot.message_handler(commands=["start"])
def cmd_start(message):
    user_id = message.from_user.id

    # أول شخص يضغط start يبقى مالك
    if not data["admins"]:
        data["admins"].append(user_id)
        save_data(data)
        bot.reply_to(
            message,
            "👑 *أهلاً بيك! أنت المالك والأدمن الأول*\n\n"
            "استخدم /help لمعرفة الأوامر",
            parse_mode="Markdown"
        )
        return

    text = (
        "🕌 *بوت البث المباشر*\n\n"
        "📺 المحطات المتاحة:\n"
        "1️⃣ الحرم المكي المشرف\n"
        "2️⃣ المسجد النبوي الشريف\n"
        "3️⃣ إذاعة القرآن - القاهرة\n\n"
        "استخدم /help لمعرفة الأوامر"
    )
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=["help"])
def cmd_help(message):
    user_id = message.from_user.id
    if is_admin(user_id):
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
            "👥 `/admins` - قائمة الأدمنز\n"
        )
    else:
        text = (
            "🕌 *أوامر المستخدم:*\n\n"
            "📊 `/status` - حالة البث\n"
            "📻 `/stations` - المحطات المتاحة\n"
        )
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=["go"])
def cmd_go(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ مش عندك صلاحية")
        return

    parts = message.text.split()
    if len(parts) < 4:
        bot.reply_to(
            message,
            "❌ *الاستخدام الصح:*\n"
            "`/go [رقم المحطة] [RTMP URL] [Stream Key]`\n\n"
            "مثال:\n"
            "`/go 1 rtmp://dc4.rtmp.t.me/live مفتاح_البث`",
            parse_mode="Markdown"
        )
        return

    station_id = parts[1]
    rtmp_url = parts[2]
    stream_key = parts[3]

    if station_id not in STATIONS:
        bot.reply_to(
            message,
            f"❌ رقم المحطة غلط، الأرقام المتاحة: 1 إلى {len(STATIONS)}"
        )
        return

    station_name = STATIONS[station_id]["name"]
    msg = bot.reply_to(message, f"⏳ جاري بدء البث...\n📺 {station_name}")

    success = start_stream(rtmp_url, stream_key, station_id)

    if success:
        time.sleep(5)
        if stream_process and stream_process.poll() is None:
            bot.edit_message_text(
                f"✅ *البث بدأ بنجاح!*\n\n"
                f"📺 المحطة: {station_name}\n"
                f"🔄 الانتقال التلقائي: مفعّل\n"
                f"🛡 المراقبة التلقائية: مفعّلة",
                msg.chat.id,
                msg.message_id,
                parse_mode="Markdown"
            )
        else:
            bot.edit_message_text(
                f"⚠️ البث بدأ لكن في مشكلة في الاتصال\n"
                f"🔄 جاري المحاولة التلقائية...",
                msg.chat.id,
                msg.message_id
            )
    else:
        bot.edit_message_text("❌ فشل بدء البث", msg.chat.id, msg.message_id)


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
    if len(parts) < 2:
        bot.reply_to(message, "❌ استخدم: `/switch [رقم]`\nمثال: `/switch 2`", parse_mode="Markdown")
        return

    station_id = parts[1]
    if station_id not in STATIONS:
        bot.reply_to(message, f"❌ رقم غلط، الأرقام من 1 إلى {len(STATIONS)}")
        return

    if not data.get("process_running"):
        bot.reply_to(message, "⚠️ البث متوقف، استخدم /go أولاً")
        return

    rtmp = data.get("rtmp_url")
    key = data.get("stream_key")

    if not rtmp or not key:
        bot.reply_to(message, "❌ مفيش RTMP محفوظ، استخدم /go من الأول")
        return

    station_name = STATIONS[station_id]["name"]
    bot.reply_to(message, f"🔀 جاري التبديل إلى:\n{station_name}")

    start_stream(rtmp, key, station_id)
    time.sleep(4)
    bot.reply_to(message, f"✅ تم التبديل إلى:\n{station_name}")


@bot.message_handler(commands=["status"])
def cmd_status(message):
    if data.get("process_running"):
        station_id = data.get("current_station", "1")
        station = STATIONS.get(station_id, {})
        name = station.get("name", "غير معروف")

        running = stream_process and stream_process.poll() is None
        status_icon = "🟢" if running else "🟡"
        status_text = "شغال" if running else "جاري إعادة التشغيل..."

        text = (
            f"{status_icon} *حالة البث: {status_text}*\n\n"
            f"📺 المحطة: {name}\n"
            f"👥 الأدمنز: {len(data['admins'])}\n"
            f"🔄 المراقبة: مفعّلة"
        )
    else:
        text = (
            "🔴 *البث متوقف*\n\n"
            "استخدم:\n"
            "`/go [رقم] [RTMP] [KEY]`\n\n"
            "مثال:\n"
            "`/go 1 rtmp://dc4.rtmp.t.me/live xxxx`"
        )
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=["stations"])
def cmd_stations(message):
    text = "📺 *المحطات المتاحة:*\n\n"
    for key, station in STATIONS.items():
        current = "🔴 بث حالي" if (
            key == data.get("current_station") and data.get("process_running")
        ) else ""
        text += f"{key}️⃣ {station['name']} {current}\n"
    text += "\nللبدء: `/go [رقم] [RTMP] [KEY]`"
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=["addadmin"])
def cmd_addadmin(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ المالك بس يقدر يضيف أدمن")
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ استخدم: `/addadmin [ID]`", parse_mode="Markdown")
        return

    try:
        new_admin = int(parts[1])
    except ValueError:
        bot.reply_to(message, "❌ الـ ID لازم يكون رقم")
        return

    if new_admin in data["admins"]:
        bot.reply_to(message, "⚠️ الشخص ده أدمن بالفعل")
        return

    data["admins"].append(new_admin)
    save_data(data)
    bot.reply_to(message, f"✅ تم إضافة `{new_admin}` كأدمن", parse_mode="Markdown")


@bot.message_handler(commands=["removeadmin"])
def cmd_removeadmin(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ المالك بس يقدر يحذف أدمن")
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ استخدم: `/removeadmin [ID]`", parse_mode="Markdown")
        return

    try:
        remove_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "❌ الـ ID لازم يكون رقم")
        return

    if remove_id == data["admins"][0]:
        bot.reply_to(message, "❌ مينفعش تحذف المالك")
        return

    if remove_id not in data["admins"]:
        bot.reply_to(message, "⚠️ الشخص ده مش أدمن")
        return

    data["admins"].remove(remove_id)
    save_data(data)
    bot.reply_to(message, f"✅ تم حذف `{remove_id}` من الأدمنز", parse_mode="Markdown")


@bot.message_handler(commands=["admins"])
def cmd_admins(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ مش عندك صلاحية")
        return

    if not data["admins"]:
        bot.reply_to(message, "مفيش أدمنز حالياً")
        return

    text = "👥 *قائمة الأدمنز:*\n\n"
    for i, admin_id in enumerate(data["admins"]):
        role = "👑 مالك" if i == 0 else "🛡 أدمن"
        text += f"{role}: `{admin_id}`\n"

    bot.reply_to(message, text, parse_mode="Markdown")


# ======= تشغيل =======
if __name__ == "__main__":
    print("✅ البوت شغال...")

    # لو في بث محفوظ، أعد تشغيله
    if data.get("process_running") and data.get("rtmp_url") and data.get("stream_key"):
        print("🔄 إعادة تشغيل البث من آخر حالة...")
        start_stream(data["rtmp_url"], data["stream_key"], data.get("current_station", "1"))

    bot.infinity_polling(timeout=60, long_polling_timeout=30)
