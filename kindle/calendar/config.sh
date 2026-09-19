# Calendar dashboard settings (sourced by calendar.sh). Unix line endings!

# Where to fetch the 758x1024 grayscale PNG from.
IMAGE_URL="https://wrightchen.github.io/kindle-calendar/calendar.png"
# LAN fallback while GitHub Pages is not up yet:
# IMAGE_URL="http://192.168.1.18:8765/calendar.png"

# MODE=battery : wake from deep sleep only at WAKE_TIMES (Beijing time), fetch, redraw, sleep again.
#                Screen keeps the image while asleep. Wi-Fi is off in between. Weeks per charge.
# MODE=powered : stay awake, fetch every INTERVAL minutes. Use when plugged in.
MODE=battery
WAKE_TIMES="00:40 07:00"
# SUSPEND=1 tries real suspend-to-RAM between wakes (best battery); after 3 early wakes
# the script gives up on it for that cycle and just idles with Wi-Fi off.
# SUSPEND=0 never suspends: always idle awake with Wi-Fi off (safe, ~2-3 days per charge).
SUSPEND=0
INTERVAL=15
# if a fetch fails in battery mode, retry after this many minutes
RETRY_MINUTES=30

# Host to ping to confirm Wi-Fi is up (your PC / router / the image server).
WIFI_TEST_IP="192.168.1.1"
