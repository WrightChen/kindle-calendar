#!/bin/sh
# Name: 日历屏保 · 安装（开机自启）
# Author: pale2

DIR=/mnt/us/calendar
SSDIR=/usr/share/blanket/screensaver
CONF=/etc/upstart/calendar-ss.conf
LOG=$DIR/ss.log

echo "Installing calendar screensaver ..."
[ -f "$DIR/ss-daemon.sh" ] || { echo "ss-daemon.sh missing in /mnt/us/calendar"; exit 1; }

# stop the always-on loop if it is running
pkill -f /mnt/us/calendar/calendar.sh 2>/dev/null
pkill -f /mnt/us/calendar/ss-daemon.sh 2>/dev/null

# diagnostics for later inspection
{
    echo "=== install $(date)"
    echo "--- screensaver dir"; ls -la "$SSDIR" 2>&1
    echo "--- upstart jobs (framework/powerd)"; initctl list 2>&1 | grep -iE 'framework|powerd|lab126_gui|blanket'
    echo "--- rtc"; ls /sys/class/rtc/ 2>&1
    echo "--- powerd"; lipc-get-prop com.lab126.powerd status 2>&1
} >>"$DIR/diag.txt" 2>&1

# back up stock screensavers once
if [ ! -d "$DIR/ss-backup" ]; then
    mkdir -p "$DIR/ss-backup"
    cp "$SSDIR"/*.png "$DIR/ss-backup/" 2>/dev/null
    echo "backed up $(ls "$DIR/ss-backup" | wc -l) stock screensaver(s)"
fi

# install upstart job
mntroot rw >/dev/null 2>&1
cat >"$CONF" <<'EOF'
# calendar screensaver daemon (/mnt/us/calendar/ss-daemon.sh)
start on started lab126_gui
stop on stopping lab126_gui

script
    exec /bin/sh /mnt/us/calendar/ss-daemon.sh
end script
EOF
sync
mntroot ro >/dev/null 2>&1
echo "installed $CONF"

start calendar-ss >/dev/null 2>&1 || /bin/sh "$DIR/ss-daemon.sh" >/dev/null 2>&1 &
echo "daemon started; first update in ~20s. Log: calendar/ss.log"
echo "Press the power button to sleep: the screensaver should be the calendar."
exit 0
