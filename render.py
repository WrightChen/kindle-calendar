#!/usr/bin/env python3
"""Render a Chinese e-ink calendar PNG for a Kindle Paperwhite 2 (758x1024, 8-bit grayscale).

Usage:
    python render.py --out site/calendar.png [--date 2026-09-19]
"""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import cnlunar
import chinese_calendar as cc
from PIL import Image, ImageDraw, ImageFont

W, H = 758, 1024
BLACK, DARK, MID, LIGHT, WHITE = 0, 70, 130, 200, 255
MARGIN = 36
TZ = ZoneInfo("Asia/Shanghai")

HERE = Path(__file__).resolve().parent
FONT_CANDIDATES = {
    "regular": [
        HERE / "fonts" / "NotoSansCJKsc-Regular.otf",
        HERE / "fonts" / "NotoSansSC-Regular.otf",
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ],
    "bold": [
        HERE / "fonts" / "NotoSansCJKsc-Bold.otf",
        HERE / "fonts" / "NotoSansSC-Bold.otf",
        Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    ],
}
WEEKDAY_CN = ["一", "二", "三", "四", "五", "六", "日"]

# cnlunar knows hundreds of obscure deity birthdays; only surface the ones people actually observe.
KNOWN_FESTIVALS = {  # substring in cnlunar name -> label to show
    "春节": "春节", "除夕": "除夕", "元宵": "元宵节", "龙抬头": "龙抬头", "清明": "清明", "端午": "端午节",
    "七夕": "七夕", "中元": "中元节", "中秋": "中秋节", "重阳": "重阳节", "腊八": "腊八", "小年": "小年",
    "元旦": "元旦", "情人节": "情人节", "妇女节": "妇女节", "植树节": "植树节", "劳动节": "劳动节",
    "青年节": "青年节", "母亲节": "母亲节", "儿童节": "儿童节", "父亲节": "父亲节", "建党": "建党节",
    "建军": "建军节", "教师节": "教师节", "国庆": "国庆节", "万圣": "万圣节", "平安夜": "平安夜",
    "圣诞": "圣诞节", "冬至": "冬至", "寒衣": "寒衣节", "下元": "下元节",
}


def known_festival(name: str) -> str | None:
    if "诞" in name and name != "圣诞节":  # deity birthdays like 弥勒佛圣诞 / 观音圣诞
        return None
    for k, label in KNOWN_FESTIVALS.items():
        if k in name:
            return label
    return None


def find_font(kind: str) -> Path:
    for p in FONT_CANDIDATES[kind]:
        if p.exists():
            return p
    sys.exit(f"No {kind} CJK font found. Put NotoSansCJKsc-{kind.title()}.otf into ./fonts/")


_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    kind = "bold" if bold else "regular"
    key = (kind, size)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(str(find_font(kind)), size)
    return _FONT_CACHE[key]


def text_w(draw: ImageDraw.ImageDraw, s: str, f: ImageFont.FreeTypeFont) -> int:
    l, t, r, b = draw.textbbox((0, 0), s, font=f)
    return r - l


def lunar_of(d: dt.date) -> cnlunar.Lunar:
    return cnlunar.Lunar(dt.datetime(d.year, d.month, d.day, 12), godType="8char")


def split_names(s: str) -> list[str]:
    return [x for x in s.replace("，", ",").replace(" ", ",").split(",") if x]


def festival_names(lun: cnlunar.Lunar) -> list[str]:
    names: list[str] = []
    for getter in (lun.get_legalHolidays, lun.get_otherLunarHolidays, lun.get_otherHolidays):
        try:
            names += split_names(getter() or "")
        except Exception:  # cnlunar is not always tidy
            pass
    # dedupe, keep order, drop the obscure ones
    seen: set[str] = set()
    out = []
    for n in names:
        k = known_festival(n)
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def cell_subtitle(d: dt.date, lun: cnlunar.Lunar) -> tuple[str, bool]:
    """Second line for a calendar cell: (text, emphasized?)."""
    fest = festival_names(lun)
    if fest:
        return fest[0], True
    if lun.todaySolarTerms and lun.todaySolarTerms != "无":
        return lun.todaySolarTerms, True
    if lun.lunarDayCn == "初一":
        return lun.lunarMonthCn.replace("小", "").replace("大", ""), False
    return lun.lunarDayCn, False


def holiday_tag(d: dt.date) -> str:
    """'休' for statutory day off that is not a normal weekend, '班' for make-up workday."""
    try:
        is_hol, name = cc.get_holiday_detail(d)
    except NotImplementedError:
        return ""
    weekend = d.weekday() >= 5
    if is_hol and name:  # named statutory holiday or its bridge day
        return "休"
    if not is_hol and weekend:
        return "班"
    return ""


def render(today: dt.date, now: dt.datetime) -> Image.Image:
    img = Image.new("L", (W, H), WHITE)
    dr = ImageDraw.Draw(img)
    lun = lunar_of(today)

    # ---------- header ----------
    y0 = 40
    day_font = font(190, bold=True)
    day_str = f"{today.day}"
    dr.text((MARGIN - 8, y0 - 30), day_str, font=day_font, fill=BLACK)
    day_w = text_w(dr, day_str, day_font)

    x_info = MARGIN + day_w + 24
    y = y0 + 4
    dr.text((x_info, y), f"{today.year}年{today.month}月", font=font(40, True), fill=BLACK)
    y += 54
    dr.text((x_info, y), f"星期{WEEKDAY_CN[today.weekday()]}", font=font(40), fill=BLACK)
    y += 60
    zodiac = f"{lun.year8Char}{lun.chineseYearZodiac}年"
    lunar_line = f"{zodiac}  {lun.lunarMonthCn.replace('小', '').replace('大', '')}{lun.lunarDayCn}"
    dr.text((x_info, y), lunar_line, font=font(28), fill=DARK)
    y += 40

    # solar-term / festival line
    fest = festival_names(lun)
    term_bits = []
    if lun.todaySolarTerms and lun.todaySolarTerms != "无":
        term_bits.append(f"今日{lun.todaySolarTerms}")
    else:
        nm, nd = lun.nextSolarTermDate
        nxt = dt.date(lun.nextSolarTermYear, nm, nd)
        term_bits.append(f"距{lun.nextSolarTerm} {(nxt - today).days} 天")
    if fest:
        term_bits.insert(0, " · ".join(fest[:2]))
    dr.text((x_info, y), "  ".join(term_bits), font=font(26, bold=bool(fest)), fill=BLACK if fest else DARK)

    tag = holiday_tag(today)
    if tag:
        # round badge at the right edge
        bx = W - MARGIN - 60
        dr.rounded_rectangle((bx, y0 + 6, bx + 60, y0 + 66), radius=12, fill=BLACK)
        f = font(36, True)
        dr.text((bx + 30 - text_w(dr, tag, f) / 2, y0 + 10), tag, font=f, fill=WHITE)

    # divider
    y_div = 240
    dr.line((MARGIN, y_div, W - MARGIN, y_div), fill=BLACK, width=3)

    # ---------- month grid ----------
    grid_top = y_div + 22
    col_w = (W - 2 * MARGIN) / 7
    head_f = font(24, True)
    for i, wd in enumerate(WEEKDAY_CN):
        cx = MARGIN + col_w * i + col_w / 2
        dr.text((cx - text_w(dr, wd, head_f) / 2, grid_top), wd, font=head_f,
                fill=MID if i >= 5 else BLACK)
    dr.line((MARGIN, grid_top + 40, W - MARGIN, grid_top + 40), fill=LIGHT, width=2)

    cal = calendar.Calendar(firstweekday=0)  # Monday first
    weeks = cal.monthdatescalendar(today.year, today.month)
    while len(weeks) < 6:  # keep a constant 6-row height
        last = weeks[-1][-1]
        weeks.append([last + dt.timedelta(days=i) for i in range(1, 8)])
    row_h = 78
    rows_top = grid_top + 52
    num_f = font(30)
    num_fb = font(30, True)
    sub_f = font(17)
    sub_fb = font(17, True)
    tag_f = font(15, True)
    for r, week in enumerate(weeks):
        for c, d in enumerate(week):
            x = MARGIN + col_w * c
            yy = rows_top + row_h * r
            cx = x + col_w / 2
            in_month = d.month == today.month
            is_today = d == today
            dl = lunar_of(d)
            sub, emph = cell_subtitle(d, dl)
            tg = holiday_tag(d) if in_month else ""

            if is_today:
                dr.rounded_rectangle((x + 4, yy - 2, x + col_w - 4, yy + row_h - 6), radius=10, fill=BLACK)
                num_fill, sub_fill = WHITE, WHITE
            elif not in_month:
                num_fill, sub_fill = LIGHT, LIGHT
            else:
                weekend = c >= 5
                num_fill = MID if weekend else BLACK
                sub_fill = DARK if emph else MID

            nf = num_fb if is_today else num_f
            ns = str(d.day)
            dr.text((cx - text_w(dr, ns, nf) / 2, yy + 4), ns, font=nf, fill=num_fill)
            sf = sub_fb if emph else sub_f
            if len(sub) > 4:
                sub = sub[:4]
            dr.text((cx - text_w(dr, sub, sf) / 2, yy + 44), sub, font=sf, fill=sub_fill)

            if tg and not is_today:
                tx = x + col_w - 24
                dr.text((tx, yy + 2), tg, font=tag_f, fill=BLACK if tg == "班" else DARK)
            elif tg and is_today:
                dr.text((x + col_w - 24, yy + 2), tg, font=tag_f, fill=WHITE)

    grid_bottom = rows_top + row_h * 6 + 4
    dr.line((MARGIN, grid_bottom, W - MARGIN, grid_bottom), fill=BLACK, width=3)

    # ---------- almanac: 宜 / 忌 ----------
    y = grid_bottom + 18
    label_f = font(26, True)
    body_f = font(22)
    good = [g for g in (lun.goodThing or []) if g][:6]
    bad = [b for b in (lun.badThing or []) if b][:6]

    def almanac_row(label: str, items: list[str], yy: int) -> None:
        dr.rounded_rectangle((MARGIN, yy, MARGIN + 40, yy + 40), radius=8, fill=BLACK)
        dr.text((MARGIN + 20 - text_w(dr, label, label_f) / 2, yy + 4), label, font=label_f, fill=WHITE)
        s = "  ".join(items) if items else "—"
        # truncate to width
        maxw = W - 2 * MARGIN - 56
        while text_w(dr, s, body_f) > maxw and len(s) > 2:
            s = s[:-2]
        dr.text((MARGIN + 56, yy + 7), s, font=body_f, fill=DARK)

    almanac_row("宜", good, y)
    almanac_row("忌", bad, y + 52)

    # ---------- year progress ----------
    y = y + 52 + 62
    doy = today.timetuple().tm_yday
    days_in_year = 366 if calendar.isleap(today.year) else 365
    pct = doy / days_in_year
    bar_x0, bar_x1 = MARGIN, W - MARGIN
    bar_y = y + 14
    dr.rounded_rectangle((bar_x0, bar_y, bar_x1, bar_y + 14), radius=7, outline=BLACK, width=2, fill=WHITE)
    dr.rounded_rectangle((bar_x0, bar_y, bar_x0 + int((bar_x1 - bar_x0) * pct), bar_y + 14), radius=7, fill=BLACK)
    iso_week = today.isocalendar()[1]
    left = days_in_year - doy
    info = f"第 {iso_week} 周 · 今年第 {doy} 天 · 已过 {pct * 100:.0f}% · 余 {left} 天"
    f = font(20)
    dr.text((MARGIN, bar_y + 26), info, font=f, fill=DARK)

    # ---------- footer ----------
    foot = f"更新 {now.strftime('%m-%d %H:%M')}"
    ff = font(16)
    dr.text((W - MARGIN - text_w(dr, foot, ff), H - 30), foot, font=ff, fill=MID)
    return img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site/calendar.png")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today in Asia/Shanghai)")
    args = ap.parse_args()

    now = dt.datetime.now(TZ)
    today = dt.date.fromisoformat(args.date) if args.date else now.date()
    img = render(today, now)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # 8-bit grayscale, no alpha: exactly what eips/fbink want
    img.convert("L").save(out, format="PNG", optimize=True)
    print(f"wrote {out} ({out.stat().st_size} bytes) for {today}")


if __name__ == "__main__":
    main()
