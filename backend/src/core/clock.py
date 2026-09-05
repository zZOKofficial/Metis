"""The one source of "now" in METIS, and it is always timezone-aware UTC.

This exists because the two stores disagree about what they hand back, and
only one of them is ever used locally. Firestore returns timezone-aware
values (`DatetimeWithNanoseconds`, UTC) for every timestamp regardless of what
was written; SQLite returns whatever was serialized. While the app wrote naive
`datetime.utcnow()`, any comparison between a stored timestamp and a freshly
computed one succeeded against SQLite on a laptop and raised

    TypeError: can't compare offset-naive and offset-aware datetimes

against the identical code path on Firestore. `GET /analytics/{id}/revenue`
with any `period` other than `all` was a 500 on the deployment and a 200
everywhere it was tested.

Keeping this in `core` rather than in the storage service lets the Pydantic
schemas share it without a model importing a service. The schemas matter for
a second reason: a naive datetime serializes without an offset, and the
browser reads an offset-less ISO string as *local* time, so timestamps were
also rendered wrong by the viewer's UTC offset.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """The current time, timezone-aware in UTC."""
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """Force a datetime into aware UTC, treating naive values as UTC.

    Naive values reaching this point were written by an older build or live in
    an existing SQLite file, and every one of those came from `utcnow()` --
    UTC with the marker dropped, not local time.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
