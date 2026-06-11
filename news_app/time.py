from datetime import UTC, datetime


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)