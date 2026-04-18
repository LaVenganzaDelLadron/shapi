import hashlib
from collections import defaultdict
from datetime import datetime, time, timedelta

from django.db.models import Avg, Count, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce, TruncDay, TruncWeek
from django.utils import timezone

from batch.models import PigBatches
from datamining.models import PigMLData
from feeding.models import Feeding
from record.models import Record


WEEKDAY_ALIASES = {
    'mon': 0,
    'monday': 0,
    'tue': 1,
    'tues': 1,
    'tuesday': 1,
    'wed': 2,
    'wednesday': 2,
    'thu': 3,
    'thur': 3,
    'thurs': 3,
    'thursday': 3,
    'fri': 4,
    'friday': 4,
    'sat': 5,
    'saturday': 5,
    'sun': 6,
    'sunday': 6,
}


def date_bounds(start_date=None, end_date=None):
    current_tz = timezone.get_current_timezone()
    range_start = None
    range_end = None

    if start_date:
        range_start = timezone.make_aware(datetime.combine(start_date, time.min), current_tz)
    if end_date:
        range_end = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min), current_tz)

    return range_start, range_end


def apply_datetime_filters(queryset, field_name, start_date=None, end_date=None):
    range_start, range_end = date_bounds(start_date=start_date, end_date=end_date)
    if range_start:
        queryset = queryset.filter(**{f'{field_name}__gte': range_start})
    if range_end:
        queryset = queryset.filter(**{f'{field_name}__lt': range_end})
    return queryset


def _rounded(value):
    return round(float(value or 0.0), 2)


def _group_series_by_batch(rows, item_builder):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['batch_code__batch_code']].append(item_builder(row))

    return [
        {
            'batch_code': batch_code,
            'series': series,
        }
        for batch_code, series in grouped.items()
    ]


def _build_growth_point(sample_time, avg_weight, pig_age_days):
    return {
        'sample_date': sample_time.isoformat(),
        'avg_weight': _rounded(avg_weight),
        'pig_age_days': int(pig_age_days),
    }


def _build_live_growth_point(batch, current_time=None):
    current_time = current_time or timezone.now()
    return _build_growth_point(
        sample_time=current_time,
        avg_weight=batch.avg_weight,
        pig_age_days=batch.get_current_age(as_of=current_time),
    )


def _should_include_live_growth_point(start_date=None, end_date=None):
    today = timezone.localdate()
    if start_date and start_date > today:
        return False
    if end_date and end_date < today:
        return False
    return True


def _parse_repeat_days(repeat_days):
    value = str(repeat_days or '').strip().lower()
    if not value or value in {'everyday', 'every day', 'daily', 'all'}:
        return None

    normalized = value.replace('/', ',').replace('|', ',')
    tokens = [token.strip() for token in normalized.split(',') if token.strip()]
    allowed_days = {WEEKDAY_ALIASES[token] for token in tokens if token in WEEKDAY_ALIASES}
    return allowed_days or None


def _adjust_to_repeat_schedule(candidate_time, repeat_days):
    allowed_days = _parse_repeat_days(repeat_days)
    if not allowed_days:
        return candidate_time

    adjusted = candidate_time
    for _ in range(7):
        if adjusted.weekday() in allowed_days:
            return adjusted
        adjusted += timedelta(days=1)
    return candidate_time


def get_growth_trends(params):
    queryset = Record.objects.select_related('batch_code').order_by('batch_code__batch_code', 'date', 'record_code')

    batch_code = params.get('batch_code')
    if batch_code:
        queryset = queryset.filter(batch_code__batch_code=batch_code)

    queryset = apply_datetime_filters(
        queryset,
        'date',
        start_date=params.get('start_date'),
        end_date=params.get('end_date'),
    )

    rows = list(queryset.values('batch_code__batch_code', 'date', 'avg_weight', 'pig_age_days'))
    latest_record_time = {}
    grouped_rows = defaultdict(list)

    for row in rows:
        batch_code_key = row['batch_code__batch_code']
        grouped_rows[batch_code_key].append({
            'sample_date': row['date'].isoformat(),
            'avg_weight': _rounded(row['avg_weight']),
            'pig_age_days': int(row['pig_age_days']),
        })
        latest_record_time[batch_code_key] = max(latest_record_time.get(batch_code_key, row['date']), row['date'])

    results = [
        {
            'batch_code': batch_code_key,
            'series': series,
        }
        for batch_code_key, series in grouped_rows.items()
    ]

    if results and _should_include_live_growth_point(
        start_date=params.get('start_date'),
        end_date=params.get('end_date'),
    ):
        now = timezone.now()
        batch_filter = PigBatches.objects.filter(batch_code__in=latest_record_time.keys())
        if batch_code:
            batch_filter = batch_filter.filter(batch_code=batch_code)

        live_batches = {batch.batch_code: batch for batch in batch_filter}
        for result in results:
            batch = live_batches.get(result['batch_code'])
            if not batch:
                continue

            latest_record = latest_record_time.get(result['batch_code'])
            if latest_record and now <= latest_record:
                continue

            result['series'].append(_build_live_growth_point(batch, now))

    return results


def get_feed_consumption(params):
    queryset = Feeding.objects.select_related('batch_code')
    batch_code = params.get('batch_code')
    if batch_code:
        queryset = queryset.filter(batch_code__batch_code=batch_code)

    queryset = apply_datetime_filters(
        queryset,
        'feed_time',
        start_date=params.get('start_date'),
        end_date=params.get('end_date'),
    )

    group_by = params.get('group_by', 'none')
    if group_by == 'none':
        aggregated = (
            queryset.values('batch_code__batch_code')
            .annotate(total_feed_quantity=Coalesce(Sum('feed_quantity'), Value(0.0)))
            .order_by('batch_code__batch_code')
        )
        return [
            {
                'batch_code': row['batch_code__batch_code'],
                'total_feed_quantity': _rounded(row['total_feed_quantity']),
            }
            for row in aggregated
        ]

    trunc_expression = TruncDay('feed_time') if group_by == 'day' else TruncWeek('feed_time')
    aggregated = (
        queryset.annotate(period=trunc_expression)
        .values('batch_code__batch_code', 'period')
        .annotate(total_feed_quantity=Coalesce(Sum('feed_quantity'), Value(0.0)))
        .order_by('batch_code__batch_code', 'period')
    )

    return _group_series_by_batch(
        aggregated,
        lambda row: {
            'period': row['period'].isoformat() if row['period'] else None,
            'total_feed_quantity': _rounded(row['total_feed_quantity']),
        },
    )


def _build_next_feeding_result(row):
    next_feeding_time = None
    if row['avg_feeding_interval_hours'] is not None:
        candidate = row['last_feed_time'] + timedelta(hours=float(row['avg_feeding_interval_hours']))
        next_feeding_time = _adjust_to_repeat_schedule(candidate, row['repeat_days'])

    return {
        'batch_code': row['batch_code'],
        'last_feed_time': row['last_feed_time'].isoformat(),
        'next_feeding_time': next_feeding_time.isoformat() if next_feeding_time else None,
        'feed_type': row['feed_type'],
        'device_code': row['device_code'],
        'repeat_days': row['repeat_days'],
    }


def get_next_feeding_schedule(params):
    latest_feeding = Feeding.objects.filter(batch_code=OuterRef('pk')).order_by('-feed_time', '-feed_code')
    latest_interval = PigMLData.objects.filter(batch_code=OuterRef('batch_code')).order_by(
        '-sample_date',
        '-record_code',
    )

    queryset = PigBatches.objects.annotate(
        last_feed_time=Subquery(latest_feeding.values('feed_time')[:1]),
        feed_type=Subquery(latest_feeding.values('feed_type')[:1]),
        device_code=Subquery(latest_feeding.values('device_code__device_code')[:1]),
        repeat_days=Subquery(latest_feeding.values('repeat_days')[:1]),
        avg_feeding_interval_hours=Subquery(latest_interval.values('avg_feeding_interval_hours')[:1]),
    ).filter(last_feed_time__isnull=False).order_by('batch_code')

    batch_code = params.get('batch_code')
    if batch_code:
        queryset = queryset.filter(batch_code=batch_code)

    return [
        _build_next_feeding_result(row)
        for row in queryset.values(
            'batch_code',
            'last_feed_time',
            'feed_type',
            'device_code',
            'repeat_days',
            'avg_feeding_interval_hours',
        )
    ]


def get_feed_dispensed_today(params):
    today = timezone.localdate()
    range_start, range_end = date_bounds(start_date=today, end_date=today)
    queryset = Feeding.objects.filter(feed_time__gte=range_start, feed_time__lt=range_end)

    batch_code = params.get('batch_code')
    if batch_code:
        queryset = queryset.filter(batch_code__batch_code=batch_code)

    if params.get('per_batch'):
        aggregated = (
            queryset.values('batch_code__batch_code')
            .annotate(total_feed_quantity=Coalesce(Sum('feed_quantity'), Value(0.0)))
            .order_by('batch_code__batch_code')
        )
        return [
            {
                'batch_code': row['batch_code__batch_code'],
                'total_feed_quantity': _rounded(row['total_feed_quantity']),
            }
            for row in aggregated
        ]

    total_feed_quantity = queryset.aggregate(
        total_feed_quantity=Coalesce(Sum('feed_quantity'), Value(0.0))
    )['total_feed_quantity']
    return {
        'date': today.isoformat(),
        'total_feed_quantity': _rounded(total_feed_quantity),
    }


def get_dashboard_overview():
    today = timezone.localdate()
    range_start, range_end = date_bounds(start_date=today, end_date=today)

    batch_totals = PigBatches.objects.aggregate(
        total_pigs=Coalesce(Sum('no_of_pigs'), Value(0)),
        active_batches=Count('id', filter=Q(no_of_pigs__gt=0)),
    )
    feeding_totals = Feeding.objects.filter(
        feed_time__gte=range_start,
        feed_time__lt=range_end,
    ).aggregate(
        total_feed_today=Coalesce(Sum('feed_quantity'), Value(0.0)),
    )
    record_totals = Record.objects.filter(
        date__gte=range_start,
        date__lt=range_end,
    ).aggregate(
        avg_weight_today=Coalesce(Avg('avg_weight'), Value(0.0)),
    )

    return {
        'total_pigs': int(batch_totals['total_pigs'] or 0),
        'active_batches': int(batch_totals['active_batches'] or 0),
        'total_feed_today': _rounded(feeding_totals['total_feed_today']),
        'avg_weight_today': _rounded(record_totals['avg_weight_today']),
    }


def _build_report_id(batch_code, start_date, end_date):
    raw = f'{batch_code}:{start_date.isoformat()}:{end_date.isoformat()}'
    digest = hashlib.md5(raw.encode('utf-8')).hexdigest()
    numeric = int(digest[:10], 16) % 10_000_000_000
    return f'RPT-{numeric:010d}'


def get_report_preview(params):
    today = timezone.localdate()
    start_date = params.get('start_date') or today
    end_date = params.get('end_date') or start_date
    range_start, range_end = date_bounds(start_date=start_date, end_date=end_date)

    batch_code = params.get('batch_code')
    batch = None
    if batch_code:
        batch = PigBatches.objects.filter(batch_code=batch_code).first()
    else:
        batch = (
            PigBatches.objects.filter(feeding__feed_time__gte=range_start, feeding__feed_time__lt=range_end)
            .distinct()
            .order_by('batch_code')
            .first()
        )
        if batch is None:
            batch = PigBatches.objects.order_by('batch_code').first()

    if batch is None:
        return {
            'report_id': _build_report_id('UNKNOWN', start_date, end_date),
            'date': end_date.isoformat(),
            'batch': {'code': None, 'name': None},
            'summary': {
                'total_scheduled_feeds': 0,
                'enabled_feeds': 0,
                'disabled_feeds': 0,
                'total_planned_feed_kg': 0.0,
                'overdue_feeds': 0,
                'automation_rate_percent': 0,
            },
            'status': {'severity': 'normal', 'needs_review': False},
            'range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
            'messages': ['No batch data is available for the selected range.'],
            'flags': {'has_overdue': False, 'is_fully_automated': False},
        }

    feedings = list(
        Feeding.objects.filter(
            batch_code=batch,
            feed_time__gte=range_start,
            feed_time__lt=range_end,
        ).order_by('feed_time', 'feed_code')
    )
    now = timezone.now()

    total_scheduled_feeds = len(feedings)
    enabled_feeds = sum(1 for feeding in feedings if feeding.feed_type == 'automatic')
    disabled_feeds = total_scheduled_feeds - enabled_feeds
    total_planned_feed_kg = _rounded(sum(feeding.feed_quantity for feeding in feedings))
    overdue_feeds = sum(1 for feeding in feedings if feeding.feed_time < now)
    automation_rate_percent = (
        round((enabled_feeds / total_scheduled_feeds) * 100)
        if total_scheduled_feeds > 0
        else 0
    )

    severity = 'critical' if overdue_feeds > 0 else 'normal'
    needs_review = overdue_feeds > 0

    messages = []
    if overdue_feeds > 0:
        messages.append(f'{overdue_feeds} feeding schedules are overdue')
        messages.append('Review required before export')
    elif total_scheduled_feeds == 0:
        messages.append('No feeding schedules found in the selected range')
    else:
        messages.append('All feeding schedules are on track')

    return {
        'report_id': _build_report_id(batch.batch_code, start_date, end_date),
        'date': end_date.isoformat(),
        'batch': {
            'code': batch.batch_code,
            'name': batch.batch_name,
        },
        'summary': {
            'total_scheduled_feeds': total_scheduled_feeds,
            'enabled_feeds': enabled_feeds,
            'disabled_feeds': disabled_feeds,
            'total_planned_feed_kg': total_planned_feed_kg,
            'overdue_feeds': overdue_feeds,
            'automation_rate_percent': automation_rate_percent,
        },
        'status': {
            'severity': severity,
            'needs_review': needs_review,
        },
        'range': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
        },
        'messages': messages,
        'flags': {
            'has_overdue': overdue_feeds > 0,
            'is_fully_automated': total_scheduled_feeds > 0 and disabled_feeds == 0,
        },
    }
