"""
Decides WHEN each platform posts.

The workflow wakes every hour and asks this module "is anyone due?". Most
hours the answer is nobody, and the run ends in seconds.

Four things this has to get right:

1. **Per-platform times.** Threads peaks on weekday mornings; Bluesky peaks on
   weekday evenings. A single shared schedule is wrong for both.

2. **GitHub's scheduler drifts.** A run booked for 20:00 can land at 20:25, or
   not at all. So a slot stays "due" for a catch-up window rather than needing
   an exact hit.

3. **A slot must fire at most once.** Every fire is recorded as
   (platform, slot-date, slot) and checked before sending. Note "slot-date",
   not "run date" -- a 23:00 slot caught at 00:20 belongs to YESTERDAY, and
   keying it on the run date would both lose the record and let it fire twice.

4. **One slot's catch-up must not swallow the next one.** Several platforms
   have slots exactly catch_up_minutes apart. Without clamping, a late run
   fires the earlier slot and then the next run fires the later one forty
   minutes afterwards -- two posts in the same hour.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
GROUP_KEYS = ["weekday", "weekend", "default"]
VALID_KEYS = set(DAY_KEYS) | set(GROUP_KEYS)

KEEP_DAYS = 21
# never let two posts land closer together than this, even after a delay
MIN_GAP_MINUTES = 45


def tz_of(cfg: dict) -> ZoneInfo:
    return ZoneInfo(cfg.get("schedule", {}).get("timezone", "Asia/Kolkata"))


def catch_up_of(cfg: dict) -> int:
    return int(cfg.get("schedule", {}).get("catch_up_minutes", 120))


def now_local(cfg: dict, override: str | None = None) -> datetime:
    # zoneinfo resolves the offset from the datetime value, so .replace() is
    # correct here (this is the pytz LMT trap, and zoneinfo does not have it).
    if override:
        return datetime.strptime(override, "%Y-%m-%d %H:%M").replace(tzinfo=tz_of(cfg))
    return datetime.now(tz_of(cfg))


def slots_for(platform_name: str, when: datetime, cfg: dict) -> list[str]:
    """The HH:MM slots this platform should post at on this date."""
    table = cfg.get("schedule", {}).get("platforms", {}).get(platform_name)
    if not table:
        return []

    day_key = DAY_KEYS[when.weekday()]
    if day_key in table:
        return list(table[day_key] or [])

    group = "weekend" if when.weekday() >= 5 else "weekday"
    if group in table:
        return list(table[group] or [])

    return list(table.get("default", []) or [])


def parse_slot(slot: str) -> tuple[int, int] | None:
    try:
        hh, mm = (int(x) for x in str(slot).split(":"))
    except (ValueError, TypeError):
        return None
    return (hh, mm) if 0 <= hh <= 23 and 0 <= mm <= 59 else None


def _ordered_slots(platform_name: str, day: datetime, cfg: dict) -> list[tuple[datetime, str]]:
    """Today's slots as real datetimes, in clock order, bad values dropped."""
    out = []
    for slot in slots_for(platform_name, day, cfg):
        parsed = parse_slot(slot)
        if parsed:
            hh, mm = parsed
            out.append((day.replace(hour=hh, minute=mm, second=0, microsecond=0), str(slot)))
    return sorted(out)


def already_fired(platform_name: str, slot_day: datetime, slot: str, state: dict) -> bool:
    day = slot_day.strftime("%Y-%m-%d")
    return slot in state.get("fired", {}).get(platform_name, {}).get(day, [])


def record_fire(platform_name: str, slot_day: datetime, slot: str, state: dict) -> None:
    day = slot_day.strftime("%Y-%m-%d")
    fired = state.setdefault("fired", {}).setdefault(platform_name, {})
    fired.setdefault(day, [])
    if slot not in fired[day]:
        fired[day].append(slot)

    # Keep the file from growing forever. 21 days is far outside any live
    # catch-up window, so this can never delete a record still in use.
    cutoff = (slot_day - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    for old in [d for d in fired if d < cutoff]:
        del fired[old]


def due_slot(platform_name: str, when: datetime, state: dict, cfg: dict) -> tuple[str, datetime] | None:
    """
    The slot this platform owes right now as (slot, slot_day), or None.

    Yesterday is checked as well as today, so a late-evening slot caught after
    midnight still goes out instead of falling into a dead zone.

    The LATEST owed slot wins: if the runner was asleep from 09:00 to 20:30,
    the 20:00 post goes out, not a stale 09:00 one.
    """
    catch_up = catch_up_of(cfg)
    candidates = []

    for offset in (0, -1):
        day = when + timedelta(days=offset)
        ordered = _ordered_slots(platform_name, day, cfg)

        for index, (slot_time, slot) in enumerate(ordered):
            window = catch_up
            if index + 1 < len(ordered):
                gap = int((ordered[index + 1][0] - slot_time).total_seconds() // 60)
                window = min(window, max(1, gap - MIN_GAP_MINUTES))

            if slot_time <= when < slot_time + timedelta(minutes=window):
                if not already_fired(platform_name, day, slot, state):
                    candidates.append((slot_time, slot, day))

    if not candidates:
        return None
    best = max(candidates)
    return best[1], best[2]


def missed_today(platform_name: str, when: datetime, state: dict, cfg: dict) -> list[str]:
    """Slots whose time has passed today without firing. Used for alerting."""
    return [
        slot
        for slot_time, slot in _ordered_slots(platform_name, when, cfg)
        if slot_time <= when and not already_fired(platform_name, when, slot, state)
    ]


def describe(platform_name: str, when: datetime, cfg: dict) -> str:
    slots = slots_for(platform_name, when, cfg)
    return ", ".join(slots) if slots else "nothing scheduled today"


def next_slot_after(platform_name: str, when: datetime, cfg: dict, search_days: int = 8) -> str:
    """Human-readable 'next post' for the status screen."""
    for offset in range(search_days):
        day = when + timedelta(days=offset)
        for slot_time, slot in _ordered_slots(platform_name, day, cfg):
            if slot_time > when:
                if offset == 0:
                    return f"today {slot}"
                if offset == 1:
                    return f"tomorrow {slot}"
                return f"{slot_time.strftime('%a')} {slot}"
    return "not scheduled"
