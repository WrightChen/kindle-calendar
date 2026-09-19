#!/bin/sh
# Name: 日历看板 · 启动
# Author: pale2
# DontUseFBInk

# Launch the dashboard loop detached from the scriptlet runner and exit.
if [ ! -f /mnt/us/calendar/calendar.sh ]; then
    eips 2 4 "calendar.sh not found in /mnt/us/calendar"
    exit 1
fi
pkill -f /mnt/us/calendar/calendar.sh 2>/dev/null
cd /mnt/us/calendar
if command -v setsid >/dev/null 2>&1; then
    setsid sh /mnt/us/calendar/calendar.sh >/dev/null 2>&1 </dev/null &
else
    nohup sh /mnt/us/calendar/calendar.sh >/dev/null 2>&1 </dev/null &
fi
exit 0
