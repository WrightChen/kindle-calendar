#!/bin/sh
# Name: 日历看板 · 停止并恢复系统
# Author: pale2
# DontUseFBInk

# Only reachable if the UI is running, i.e. after a reboot. Kept for completeness:
# it kills a stray loop and makes sure the normal UI is back.
pkill -f /mnt/us/calendar/calendar.sh 2>/dev/null
lipc-set-prop com.lab126.powerd preventScreenSaver 0
/etc/init.d/framework start >/dev/null 2>&1 &
exit 0
