from datetime import UTC, datetime, timedelta


def get_now_utc() -> datetime:
    return datetime.now(UTC)


LOCAL_UTC_OFFSET = timedelta(hours=5)
"""Kazakhstan's single time zone (Asia/Almaty) since March 2024.

Technical timestamps (`created_at`, `watched_at`, ...) are UTC. Anything
that means "today" to the two users, such as an action's `due_date`, is
local.
"""


def get_local_now() -> datetime:
    """Local wall-clock time in Kazakhstan, naive"""
    return (datetime.now(UTC) + LOCAL_UTC_OFFSET).replace(tzinfo=None)
