#!/usr/bin/env python3
"""知乎日历风格：大日期 + 每日一问 + 一段回答。758x1024 灰度 PNG。

    python render_qa.py --out site/calendar.png [--date 2026-09-19]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from render import (BLACK, DARK, H, LIGHT, MARGIN, MID, TZ, W, WEEKDAY_CN, WHITE, festival_names, font,
                    holiday_tag, lunar_of, text_w)

HERE = Path(__file__).resolve().parent
DAILY = HERE / "daily.json"


def wrap_cjk(draw: ImageDraw.ImageDraw, s: str, f: ImageFont.FreeTypeFont, maxw: int) -> list[str]:
    """Character-based wrapping (CJK has no spaces); keeps closing punctuation off line starts."""
    lines: list[str] = []
    cur = ""
    for ch in s:
        if text_w(draw, cur + ch, f) <= maxw:
            cur += ch
        else:
            if ch in "，。！？；：、”』」）》" and cur:
                cur += ch
                lines.append(cur)
                cur = ""
                continue
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def load_entries() -> list[dict]:
    """All daily*.json files in the project folder, concatenated (so the bank can grow in themed files)."""
    entries: list[dict] = []
    for p in sorted(HERE.glob("daily*.json")):
        entries += json.loads(p.read_text(encoding="utf-8"))
    return entries


def pick_entry(today: dt.date) -> dict:
    entries = load_entries()
    # deterministic per day, but shuffled so consecutive days do not walk the file in order
    h = int(hashlib.sha1(today.isoformat().encode()).hexdigest(), 16)
    return entries[h % len(entries)]


def render(today: dt.date, now: dt.datetime) -> Image.Image:
    img = Image.new("L", (W, H), WHITE)
    dr = ImageDraw.Draw(img)
    lun = lunar_of(today)

    # ---- top strip: year.month left, weekday right ----
    y = 44
    f_small = font(26)
    dr.text((MARGIN, y), f"{today.year}.{today.month:02d}", font=f_small, fill=DARK)
    wd = f"星期{WEEKDAY_CN[today.weekday()]}"
    dr.text((W - MARGIN - text_w(dr, wd, f_small), y), wd, font=f_small, fill=DARK)

    # ---- huge day number, centered ----
    f_day = font(300, bold=True)
    ds = f"{today.day:02d}"
    dw = text_w(dr, ds, f_day)
    dr.text(((W - dw) / 2, 60), ds, font=f_day, fill=BLACK)

    # ---- lunar / term / festival line ----
    y = 420
    month_cn = lun.lunarMonthCn.replace("小", "").replace("大", "")
    bits = [f"{lun.year8Char}{lun.chineseYearZodiac}年", f"{month_cn}{lun.lunarDayCn}"]
    if lun.todaySolarTerms and lun.todaySolarTerms != "无":
        bits.append(lun.todaySolarTerms)
    else:
        nm, nd = lun.nextSolarTermDate
        nxt = dt.date(lun.nextSolarTermYear, nm, nd)
        bits.append(f"距{lun.nextSolarTerm}{(nxt - today).days}天")
    fest = festival_names(lun)
    bits = fest[:1] + bits
    line = " · ".join(bits)
    f_l = font(26)
    dr.text(((W - text_w(dr, line, f_l)) / 2, y), line, font=f_l, fill=DARK)

    tag = holiday_tag(today)
    if tag:
        bx = W - MARGIN - 56
        dr.rounded_rectangle((bx, 90, bx + 56, 146), radius=10, fill=BLACK)
        f = font(34, True)
        dr.text((bx + 28 - text_w(dr, tag, f) / 2, 94), tag, font=f, fill=WHITE)

    # ---- divider ----
    y = 490
    dr.line((W / 2 - 40, y, W / 2 + 40, y), fill=BLACK, width=3)

    # ---- question + answer, vertically centred in the lower half ----
    entry = pick_entry(today)
    maxw = W - 2 * MARGIN - 24
    f_q = font(42, bold=True)
    f_a = font(28)
    f_b = font(22)
    q_lines = wrap_cjk(dr, entry["q"], f_q, maxw)[:4]
    a_lines = wrap_cjk(dr, entry["a"], f_a, maxw)
    max_lines = 9
    if len(a_lines) > max_lines:
        a_lines = a_lines[:max_lines]
        a_lines[-1] = a_lines[-1][:-1] + "…"
    block_h = len(q_lines) * 60 + 34 + len(a_lines) * 46 + 40
    top, bottom = 520, H - 90
    y = top + max(0, (bottom - top - block_h) // 2)

    for ln in q_lines:
        dr.text(((W - text_w(dr, ln, f_q)) / 2, y), ln, font=f_q, fill=BLACK)
        y += 60
    y += 34
    for ln in a_lines:
        dr.text(((W - text_w(dr, ln, f_a)) / 2, y), ln, font=f_a, fill=DARK)
        y += 46
    by = f"—— {entry.get('by', '')}".strip()
    if len(by) > 3:
        dr.text((W - MARGIN - 12 - text_w(dr, by, f_b), y + 8), by, font=f_b, fill=MID)

    # ---- footer ----
    doy = today.timetuple().tm_yday
    foot = f"第 {today.isocalendar()[1]} 周 · 今年第 {doy} 天"
    f_f = font(20)
    dr.text((MARGIN, H - 44), foot, font=f_f, fill=MID)
    upd = f"更新 {now.strftime('%m-%d %H:%M')}"
    f_u = font(16)
    dr.text((W - MARGIN - text_w(dr, upd, f_u), H - 40), upd, font=f_u, fill=LIGHT)
    return img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site/calendar.png")
    ap.add_argument("--date")
    args = ap.parse_args()
    now = dt.datetime.now(TZ)
    today = dt.date.fromisoformat(args.date) if args.date else now.date()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    render(today, now).convert("L").save(out, format="PNG", optimize=True)
    print(f"wrote {out} for {today}")


if __name__ == "__main__":
    main()
