#!/bin/bash
# stream.sh - سكريبت البث المباشر مع fallback تلقائي

RTMP_DEST="${RTMP_URL}/${STREAM_KEY}"

# قائمة المحطات مرتبة
declare -A STATION_NAMES=(
  [1]="إذاعة القرآن الكريم - القاهرة"
  [2]="إذاعة القرآن الكريم - السعودية"
  [3]="إذاعة نور القرآن - إيران"
  [4]="إذاعة القرآن الكريم - المغرب"
  [5]="إذاعة الإيمان - السعودية"
  [6]="إذاعة القرآن الكريم - الكويت"
  [7]="إذاعة المجد للقرآن"
  [8]="إذاعة القرآن الكريم - تونس"
  [9]="إذاعة القرآن الكريم - الجزائر"
  [10]="إذاعة الرحمة الإسلامية"
)

declare -A STATION_URLS=(
  [1]="http://stream.radiotime.com/listen.stream?streamid=3538"
  [2]="http://stream.radiotime.com/listen.stream?streamid=2019"
  [3]="http://live.mp3quran.net:9728/"
  [4]="http://stream.radiotime.com/listen.stream?streamid=2748"
  [5]="http://live.mp3quran.net:9708/"
  [6]="http://stream.radiotime.com/listen.stream?streamid=2773"
  [7]="http://live.mp3quran.net:9706/"
  [8]="http://stream.radiotime.com/listen.stream?streamid=3437"
  [9]="http://stream.radiotime.com/listen.stream?streamid=3512"
  [10]="http://live.mp3quran.net:9710/"
)

declare -A BACKUP_URLS=(
  [1]="http://live.mp3quran.net:9722/"
  [2]="http://live.mp3quran.net:9714/"
  [3]="http://stream.zeno.fm/0r0xa792kwzuv"
  [4]="http://live.mp3quran.net:9730/"
  [5]="http://stream.zeno.fm/4d0zqz1vd0zuv"
  [6]="http://live.mp3quran.net:9718/"
  [7]="http://stream.zeno.fm/q5kfmk8emhzuv"
  [8]="http://live.mp3quran.net:9724/"
  [9]="http://live.mp3quran.net:9726/"
  [10]="http://stream.zeno.fm/4d0zqz1vd0zuv"
)

TOTAL_STATIONS=10
STREAM_DURATION=6900  # 115 دقيقة (أقل من حد الـ 2 ساعة)
END_TIME=$((SECONDS + STREAM_DURATION))

current=1
fail_count=0
use_backup=false

do_stream() {
  local station_id=$1
  local url=$2
  local name="${STATION_NAMES[$station_id]}"

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📻 المحطة: $name"
  echo "🔗 الرابط: $url"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  timeout 300 ffmpeg \
    -reconnect 1 \
    -reconnect_streamed 1 \
    -reconnect_delay_max 5 \
    -timeout 10000000 \
    -i "$url" \
    -vn \
    -c:a aac \
    -b:a 128k \
    -ar 44100 \
    -ac 2 \
    -f flv \
    -loglevel warning \
    "$RTMP_DEST"

  return $?
}

echo "🚀 بدء البث - $(date)"
echo "🎯 الوجهة: $RTMP_DEST"

while [ $SECONDS -lt $END_TIME ]; do
  remaining=$((END_TIME - SECONDS))
  echo ""
  echo "⏱ الوقت المتبقي: ${remaining}s"

  if $use_backup; then
    url="${BACKUP_URLS[$current]}"
    echo "🔄 محاولة الرابط الاحتياطي..."
  else
    url="${STATION_URLS[$current]}"
  fi

  do_stream "$current" "$url"
  exit_code=$?

  if [ $exit_code -eq 0 ] || [ $exit_code -eq 124 ]; then
    # timeout طبيعي - استمر من نفس المحطة
    use_backup=false
    fail_count=0
    echo "✅ انتهى المقطع، استمرار..."
    continue
  fi

  fail_count=$((fail_count + 1))
  echo "⚠️ فشل البث (محاولة $fail_count)"

  if [ $fail_count -eq 1 ] && ! $use_backup; then
    echo "🔄 تجربة الرابط الاحتياطي..."
    use_backup=true
    sleep 2
  else
    # الانتقال للمحطة التالية
    next=$(( (current % TOTAL_STATIONS) + 1 ))
    echo "⏭ الانتقال من المحطة $current إلى المحطة $next"
    echo "📻 ${STATION_NAMES[$next]}"
    current=$next
    use_backup=false
    fail_count=0
    sleep 3
  fi
done

echo ""
echo "✅ انتهت الجلسة - $(date)"
echo "🔄 سيتم إعادة التشغيل تلقائياً بالـ schedule"
