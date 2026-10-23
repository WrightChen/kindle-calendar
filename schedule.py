#!/usr/bin/env python3
"""No-repeat rotation for the daily card.

schedule.json is the record of which entry is (or will be) shown on which date. Extending it
picks, for each new date, an entry not yet used in the current cycle; a new cycle starts only
after every entry has been shown once. Entries added later simply join the unused pool, and
past dates never change.

    python schedule.py --days 14          # make sure today .. today+13 are scheduled
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
SCHEDULE = HERE / "schedule.json"
TZ = ZoneInfo("Asia/Shanghai")


def load_entries() -> list[dict]:
    entries: list[dict] = []
    for p in sorted(HERE.glob("daily*.json")):
        entries += json.loads(p.read_text(encoding="utf-8"))
    return entries


def entry_text(e: dict) -> str:
    return e.get("quote") or e.get("q") or ""


def entry_id(e: dict) -> str:
    """Stable id from the card's main text, so reordering or splitting files does not matter."""
    return hashlib.sha1(entry_text(e).strip().encode("utf-8")).hexdigest()[:12]


def entry_kind(e: dict) -> str:
    return "quote" if "quote" in e else e.get("tag", "")


def load_schedule() -> list[dict]:
    if SCHEDULE.exists():
        return json.loads(SCHEDULE.read_text(encoding="utf-8"))
    return []


def save_schedule(rows: list[dict]) -> None:
    rows.sort(key=lambda r: r["date"])
    SCHEDULE.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def extend(rows: list[dict], entries: list[dict], until: dt.date) -> int:
    by_id = {entry_id(e): e for e in entries}
    rows.sort(key=lambda r: r["date"])
    # rebuild the current cycle's used set from history
    used: set[str] = set()
    for r in rows:
        if r["id"] in by_id:
            used.add(r["id"])
        if set(by_id) <= used:
            used = set()
    last = dt.date.fromisoformat(rows[-1]["date"]) if rows else None
    prev_kind = entry_kind(by_id[rows[-1]["id"]]) if rows and rows[-1]["id"] in by_id else ""
    start = (last + dt.timedelta(days=1)) if last else dt.datetime.now(TZ).date()
    added = 0
    d = start
    while d <= until:
        pool = [i for i in by_id if i not in used]
        if not pool:
            used = set()
            pool = list(by_id)
        # fixed pseudo-random order, salted per cycle so each cycle has a fresh order
        cycle_salt = str(sum(1 for r in rows if r["id"] in by_id) // max(1, len(by_id)))
        pool.sort(key=lambda i: hashlib.sha1((cycle_salt + i).encode()).hexdigest())
        # prefer a different kind of card than yesterday (quote vs. tag), if any is available
        pick = next((i for i in pool if entry_kind(by_id[i]) != prev_kind), pool[0])
        e = by_id[pick]
        rows.append({"date": d.isoformat(), "id": pick, "kind": entry_kind(e), "text": entry_text(e)[:24]})
        used.add(pick)
        prev_kind = entry_kind(e)
        d += dt.timedelta(days=1)
        added += 1
    return added


def lookup(date: dt.date) -> dict | None:
    """Entry scheduled for `date`, or None if the date is not in schedule.json."""
    by_id = {entry_id(e): e for e in load_entries()}
    for r in load_schedule():
        if r["date"] == date.isoformat():
            return by_id.get(r["id"])
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    args = ap.parse_args()
    today = dt.datetime.now(TZ).date()
    rows = load_schedule()
    n = extend(rows, load_entries(), today + dt.timedelta(days=args.days - 1))
    save_schedule(rows)
    print(f"schedule.json: +{n} day(s), {len(rows)} total, last {rows[-1]['date'] if rows else '-'}")


if __name__ == "__main__":
    main()
