"""Completed Tokyo sessions, with the existing 16:00 JST data-release buffer."""
from datetime import datetime, time, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo
import exchange_calendars as xcals


@lru_cache(maxsize=4)
def calendar(year):
    return xcals.get_calendar('XTKS', start=f'{year-1}-01-01', end=f'{year+1}-12-31')


def expected_price_date(now):
    if now.tzinfo is None:
        raise ValueError('Timezone-aware time is required')
    local = now.astimezone(ZoneInfo('Asia/Tokyo'))
    day = local.date() if local.time() >= time(16) else local.date()-timedelta(days=1)
    return calendar(day.year).date_to_session(day.isoformat(), direction='previous').date().isoformat()


def expected_eod_date(as_of):
    return expected_price_date(datetime.fromisoformat(as_of+'T16:00:00+09:00'))
