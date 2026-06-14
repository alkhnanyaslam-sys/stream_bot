# stations.py - قائمة جميع محطات الإذاعة

STATIONS = {
    "1": {
        "name": "📻 إذاعة القرآن الكريم - القاهرة",
        "url": "http://stream.radiotime.com/listen.stream?streamid=3538",
        "backup": "http://live.mp3quran.net:9722/",
    },
    "2": {
        "name": "🕌 إذاعة القرآن الكريم - السعودية",
        "url": "http://stream.radiotime.com/listen.stream?streamid=2019",
        "backup": "http://live.mp3quran.net:9714/",
    },
    "3": {
        "name": "🌙 إذاعة نور القرآن - إيران",
        "url": "http://live.mp3quran.net:9728/",
        "backup": "http://stream.zeno.fm/0r0xa792kwzuv",
    },
    "4": {
        "name": "⭐ إذاعة القرآن الكريم - المغرب",
        "url": "http://stream.radiotime.com/listen.stream?streamid=2748",
        "backup": "http://live.mp3quran.net:9730/",
    },
    "5": {
        "name": "🌟 إذاعة الإيمان - السعودية",
        "url": "http://live.mp3quran.net:9708/",
        "backup": "http://stream.zeno.fm/4d0zqz1vd0zuv",
    },
    "6": {
        "name": "🕋 إذاعة القرآن الكريم - الكويت",
        "url": "http://stream.radiotime.com/listen.stream?streamid=2773",
        "backup": "http://live.mp3quran.net:9718/",
    },
    "7": {
        "name": "📖 إذاعة المجد للقرآن الكريم",
        "url": "http://live.mp3quran.net:9706/",
        "backup": "http://stream.zeno.fm/q5kfmk8emhzuv",
    },
    "8": {
        "name": "🌺 إذاعة القرآن الكريم - تونس",
        "url": "http://stream.radiotime.com/listen.stream?streamid=3437",
        "backup": "http://live.mp3quran.net:9724/",
    },
    "9": {
        "name": "🌸 إذاعة القرآن الكريم - الجزائر",
        "url": "http://stream.radiotime.com/listen.stream?streamid=3512",
        "backup": "http://live.mp3quran.net:9726/",
    },
    "10": {
        "name": "🎙️ إذاعة الرحمة الإسلامية",
        "url": "http://live.mp3quran.net:9710/",
        "backup": "http://stream.zeno.fm/4d0zqz1vd0zuv",
    },
}

# الترتيب الافتراضي للمحطات (fallback chain)
STATION_ORDER = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
