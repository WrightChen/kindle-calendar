#!/bin/sh
# Kindle-side dashboard loop: fetch calendar.png, draw it, sleep, repeat.
# Lives in /mnt/us/calendar/. Started by Calendar-Start.sh, stopped by Calendar-Stop.sh.

DIR=/mnt/us/calendar
. "$DIR/config.sh"
LOG="$DIR/calendar.log"

log() { echo "$(date '+%m-%d %H:%M:%S') $*" >>"$LOG"; }

# keep the log small
[ -f "$LOG" ] && [ "$(wc -c <"$LOG")" -gt 200000 ] && tail -c 50000 "$LOG" >"$LOG.tmp" && mv "$LOG.tmp" "$LOG"

log "=== calendar.sh starting (mode $MODE, suspend $SUSPEND, uptime $(cut -d' ' -f1 /proc/uptime)s, url $IMAGE_URL)"

# Take over the screen: stop the Kindle UI, keep the device awake, keep Wi-Fi on.
take_over_screen() {
    /etc/init.d/framework stop >/dev/null 2>&1
    initctl stop webreader >/dev/null 2>&1
    lipc-set-prop com.lab126.powerd preventScreenSaver 1
}
take_over_screen
lipc-set-prop com.lab126.cmd wirelessEnable 1
echo powersave >/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null

eips -c
eips 2 4 "Calendar: waiting for Wi-Fi ..."

wait_wifi() {
    i=0
    while ! ping -c 1 -W 2 "$WIFI_TEST_IP" >/dev/null 2>&1; do
        i=$((i + 1))
        [ $i -ge 45 ] && return 1
        sleep 2
    done
    return 0
}

# Download with the stock wget; fall back to the bundled static `xh` (modern TLS) for https hosts.
fetch_image() {
    out="$1"
    url="${IMAGE_URL}?t=$(date +%s)"
    if wget -q -T 30 -O "$out" "$url" 2>>"$LOG"; then
        return 0
    fi
    if [ -x "$DIR/bin/xh" ]; then
        log "wget failed, trying xh"
        "$DIR/bin/xh" -q -d -o "$out" --timeout 30 get "$url" 2>>"$LOG" && return 0
    fi
    return 1
}

# one-time capability probe, useful when moving the image to an https host
if wget -q -T 20 -O /dev/null "https://github.com/" 2>>"$LOG"; then
    log "https probe: OK"
else
    log "https probe: FAILED (use http:// image url)"
fi

# seconds from now until the next HH:MM in WAKE_TIMES (Beijing = UTC+8, pure arithmetic, busybox-safe)
secs_until_next_wake() {
    now=$(date -u +%s)
    day_sec=$(( (now + 8 * 3600) % 86400 ))
    best=86400
    for t in $WAKE_TIMES; do
        h=$(echo "${t%%:*}" | sed 's/^0*//'); m=$(echo "${t##*:}" | sed 's/^0*//')
        [ -z "$h" ] && h=0; [ -z "$m" ] && m=0
        target=$(( h * 3600 + m * 60 ))
        d=$(( target - day_sec ))
        [ $d -le 60 ] && d=$(( d + 86400 ))
        [ $d -lt $best ] && best=$d
    done
    echo $best
}

framework_running() {
    pgrep -f cvm >/dev/null 2>&1 || pgrep -f lab126_gui >/dev/null 2>&1
}

# Sleep until $1 seconds from now. Tries a real suspend-to-RAM with an RTC alarm;
# if the device refuses or keeps waking early, fall back to staying awake with Wi-Fi off
# (still cheap on power, and never spins).
early_wakes=0
deep_sleep() {
    secs=$1
    target=$(( $(date -u +%s) + secs ))
    log "sleeping ${secs}s (wake $(date -u -d @$(( target + 8 * 3600 )) '+%H:%M' 2>/dev/null) Beijing)"
    lipc-set-prop com.lab126.cmd wirelessEnable 0
    sync
    sleep 3

    while :; do
        remain=$(( target - $(date -u +%s) ))
        [ $remain -le 30 ] && break

        if [ "$SUSPEND" = "1" ] && [ $early_wakes -lt 3 ]; then
            log "suspend: powerd=$(lipc-get-prop com.lab126.powerd status 2>&1 | tr '\n' ' ') rtc1=$(cat /sys/class/rtc/rtc1/wakealarm 2>/dev/null)"
            lipc-set-prop -i com.lab126.powerd rtcWakeup "$remain" 2>>"$LOG"
            t0=$(date -u +%s)
            err=$(echo mem 2>&1 >/sys/power/state)
            slept=$(( $(date -u +%s) - t0 ))
            log "resume after ${slept}s ${err:+(error: $err)}"
            if [ $slept -lt 120 ] && [ $remain -gt 300 ]; then
                early_wakes=$((early_wakes + 1))
                log "early wake #$early_wakes"
                [ $early_wakes -ge 3 ] && log "suspend unreliable on this firmware, staying awake instead"
            fi
            if framework_running; then
                log "UI came back after resume, stopping it again"
                take_over_screen
                [ -f "$DIR/dash.png" ] && eips -f -g "$DIR/dash.png"
            fi
            sleep 5
        else
            # plain wait, in chunks so the loop can notice the clock
            chunk=$remain; [ $chunk -gt 900 ] && chunk=900
            sleep $chunk
        fi
    done
    log "wake time reached"
    early_wakes=0
    lipc-set-prop com.lab126.cmd wirelessEnable 1
    sleep 8
}

last=""
fails=0
while true; do
    ok=0
    if ! wait_wifi; then
        log "no Wi-Fi (cannot ping $WIFI_TEST_IP), toggling radio"
        lipc-set-prop com.lab126.cmd wirelessEnable 0
        sleep 5
        lipc-set-prop com.lab126.cmd wirelessEnable 1
        if [ "$MODE" = "battery" ]; then
            deep_sleep $((RETRY_MINUTES * 60))
        else
            sleep 60
        fi
        continue
    fi

    if fetch_image "$DIR/new.png" && [ -s "$DIR/new.png" ]; then
        fails=0
        ok=1
        sum=$(md5sum "$DIR/new.png" | cut -d' ' -f1)
        if [ "$sum" != "$last" ]; then
            mv "$DIR/new.png" "$DIR/dash.png"
            eips -f -g "$DIR/dash.png"
            last="$sum"
            log "updated screen ($sum)"
        else
            rm -f "$DIR/new.png"
            log "no change"
        fi
    else
        fails=$((fails + 1))
        rm -f "$DIR/new.png"
        log "fetch failed ($fails)"
        if [ $fails -ge 3 ] && [ -f "$DIR/dash.png" ]; then
            # tiny corner marker so you can see it is stale
            eips 0 39 "offline $(date '+%H:%M')"
        fi
    fi

    if [ "$MODE" = "battery" ]; then
        if [ $ok -eq 1 ]; then
            deep_sleep "$(secs_until_next_wake)"
        else
            deep_sleep $((RETRY_MINUTES * 60))
        fi
    else
        sleep $((INTERVAL * 60))
    fi
done
