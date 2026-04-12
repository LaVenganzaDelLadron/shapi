from datetime import timezone as dt_timezone

from django.utils import timezone


UTC = dt_timezone.utc


def ensure_aware_utc(value):
    if value is None:
        value = timezone.now()
    if timezone.is_naive(value):
        value = timezone.make_aware(value, UTC)
    return value.astimezone(UTC)


def utc_date(value=None):
    return ensure_aware_utc(value).date()


def calculate_batch_age(started_at, as_of=None):
    if started_at is None:
        return 0

    start_date = utc_date(started_at)
    target_date = utc_date(as_of)
    return max((target_date - start_date).days, 0)
