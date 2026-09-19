#!/bin/sh
# Screensaver-mode daemon. The Kindle UI keeps running and sleeping normally; this script
# listens to powerd events, wakes the device once a day via the RTC alarm, fetches the
# calendar image, writes it over the system screensaver images and redraws the screen.
# Started by /etc/upstart/calendar-ss.conf (installed by Calendar-SS-Install.sh).

DIR=/mnt/us/calendar
. "$DIR/config.sh"
LOG="$DIR/ss.log"
SSDIR=/usr/share/blanket/screensaver
STAMP="$DIR/last_ok"

log() { echo "$(date -u -d @$(( $(date -u +%s) + 8 * 3600 )) '+%m-%d %H:%M:%S') $*" >>"$LOG"; }
[ -f "$LOG" ] && [ "$(wc -c <"$LOG")" -gt 200000 ] && tail -c 50000 "$LOG" >"$LOG.tmp" && mv "$LOG.tmp" "$LOG"

beijing_date() { date -u -d @$(( $(date -u +%s) + 8 * 3600 )) +%Y-%m-%d; }

secs_until_next_wake() {
    now=$(date -u +%s)
    day_sec=$(( (now + 8 * 3600) % 86400 ))
    best=86400
    for t in $WAKE_TIMES; do
        h=$(echo "${t%%:*}" | sed 's/^0*//'); m=$(echo "${t##*:}" | sed 's/^0*//')
        [ -z "$h" ] && h=0; [ -z "$m" ] && m=0
        d=$(( h * 3600 + m * 60 - day_sec ))
        [ $d -le 60 ] && d=$(( d + 86400 ))
        [ $d -lt $best ] && best=$d
    done
    echo $best
}

fetch_image() {
    out="$1"; url="${IMAGE_URL}?t=$(date +%s)"
    wget -q -T 30 -O "$out" "$url" 2>>"$LOG" && return 0
    [ -x "$DIR/bin/xh" ] && "$DIR/bin/xh" -q -d -o "$out" --timeout 30 get "$url" 2>>"$LOG" && return 0
    return 1
}

wait_wifi() {
    i=0
    while ! ping -c 1 -W 2 "$WIFI_TEST_IP" >/dev/null 2>&1; do
        i=$((i + 1)); [ $i -ge 25 ] && return 1
        sleep 2
    done
}

# copy dash.png over every stock screensaver image (originals were backed up by the installer)
apply_to_screensaver() {
    mntroot rw >/dev/null 2>&1
    n=0
    for f in "$SSDIR"/*.png; do
        [ -f "$f" ] || continue
        cp "$DIR/dash.png" "$f" && n=$((n + 1))
    done
    sync
    mntroot ro >/dev/null 2>&1
    log "wrote calendar into $n screensaver file(s)"
}

redraw_if_asleep() {
    st=$(lipc-get-prop com.lab126.powerd status 2>/dev/null)
    case "$st" in
        *"Screen Saver"*) eips -f -g "$DIR/dash.png"; log "redrew screen (state: Screen Saver)";;
        *) log "not redrawing, powerd state: $(echo "$st" | head -1)";;
    esac
}

update() {
    log "update: start (reason: $1)"
    # ask powerd not to suspend for a while (property exists on 5.x; ignore if not)
    lipc-set-prop -i com.lab126.powerd deferSuspend 120000 >/dev/null 2>&1
    was_wifi=$(lipc-get-prop com.lab126.cmd wirelessEnable 2>/dev/null)
    [ "$was_wifi" = "1" ] || lipc-set-prop com.lab126.cmd wirelessEnable 1
    if ! wait_wifi; then
        log "update: no Wi-Fi"
    elif fetch_image "$DIR/new.png" && [ -s "$DIR/new.png" ]; then
        sum=$(md5sum "$DIR/new.png" | cut -d' ' -f1)
        old=$(md5sum "$DIR/dash.png" 2>/dev/null | cut -d' ' -f1)
        mv "$DIR/new.png" "$DIR/dash.png"
        if [ "$sum" != "$old" ]; then
            apply_to_screensaver
            redraw_if_asleep
        else
            log "update: image unchanged"
        fi
        beijing_date >"$STAMP"
    else
        rm -f "$DIR/new.png"
        log "update: fetch failed"
    fi
    # restore the radio state the user had (off when it was off)
    [ "$was_wifi" = "1" ] || lipc-set-prop com.lab126.cmd wirelessEnable 0
    log "update: done"
}

stale() { [ "$(cat "$STAMP" 2>/dev/null)" != "$(beijing_date)" ]; }

log "=== ss-daemon starting (uptime $(cut -d' ' -f1 /proc/uptime)s, wake times: $WAKE_TIMES)"
sleep 20   # let the UI finish booting
stale && update boot

lipc-wait-event -m com.lab126.powerd goingToScreenSaver,wakeupFromSuspend,readyToSuspend 2>>"$LOG" | while read ev; do
    case "$ev" in
        readyToSuspend*)
            secs=$(secs_until_next_wake)
            lipc-set-prop -i com.lab126.powerd rtcWakeup "$secs" 2>>"$LOG"
            log "readyToSuspend: RTC alarm in ${secs}s"
            ;;
        wakeupFromSuspend*)
            sleep 2
            if stale; then update wakeup; else log "wakeup: already updated today"; fi
            ;;
        goingToScreenSaver*)
            if stale; then update screensaver; fi
            ;;
    esac
done
log "event loop ended"
