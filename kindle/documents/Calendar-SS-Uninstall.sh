#!/bin/sh
# Name: 日历屏保 · 卸载并还原原屏保
# Author: pale2

DIR=/mnt/us/calendar
SSDIR=/usr/share/blanket/screensaver
CONF=/etc/upstart/calendar-ss.conf

echo "Removing calendar screensaver ..."
stop calendar-ss >/dev/null 2>&1
pkill -f /mnt/us/calendar/ss-daemon.sh 2>/dev/null

mntroot rw >/dev/null 2>&1
rm -f "$CONF"
if [ -d "$DIR/ss-backup" ]; then
    cp "$DIR/ss-backup"/*.png "$SSDIR"/ 2>/dev/null && echo "stock screensavers restored"
fi
sync
mntroot ro >/dev/null 2>&1
rm -f "$DIR/last_ok"
echo "done. Reboot to be sure."
exit 0
