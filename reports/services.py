import hashlib
from collections import defaultdict
from datetime import datetime, time, timedelta

from django.utils import timezone

from feeding.models import Feeding


def _date_bounds(start_date=None, end_date=None):
    current_tz = timezone.get_current_timezone()
    range_start = None
    range_end = None

    if start_date:
        range_start = timezone.make_aware(datetime.combine(start_date, time.min), current_tz)
    if end_date:
        range_end = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min), current_tz)

    return range_start, range_end


def _build_report_id(batch_code, report_date):
    raw = f'{batch_code}:{report_date.isoformat()}'
    digest = hashlib.md5(raw.encode('utf-8')).hexdigest()
    numeric = int(digest[:10], 16) % 10_000_000_000
    return f'RPT-{numeric:010d}'


def _status_for_packet(overdue_feeds, disabled_feeds):
    if overdue_feeds > 0:
        return 'review'
    if disabled_feeds > 0:
        return 'draft'
    return 'published'


def _messages_for_packet(overdue_feeds, total_scheduled_feeds):
    if overdue_feeds > 0:
        return [
            f'{overdue_feeds} feeding schedules are overdue',
            'Review required before export',
        ]
    if total_scheduled_feeds == 0:
        return ['No feeding schedules found in the selected range']
    return ['All feeding schedules are on track']


def _packet_from_group(batch_code, batch_name, report_date, rows, now):
    total_scheduled_feeds = len(rows)
    enabled_feeds = sum(1 for row in rows if row.feed_type == 'automatic')
    disabled_feeds = total_scheduled_feeds - enabled_feeds
    total_planned_feed_kg = round(sum(row.feed_quantity for row in rows), 2)
    overdue_feeds = sum(1 for row in rows if row.feed_time < now)
    automation_rate_percent = (
        round((enabled_feeds / total_scheduled_feeds) * 100)
        if total_scheduled_feeds > 0
        else 0
    )

    severity = 'critical' if overdue_feeds > 0 else 'normal'
    needs_review = overdue_feeds > 0
    workflow_status = _status_for_packet(overdue_feeds, disabled_feeds)
    messages = _messages_for_packet(overdue_feeds, total_scheduled_feeds)

    return {
        'report_id': _build_report_id(batch_code, report_date),
        'date': report_date.isoformat(),
        'owner': 'Admin',
        'workflow_status': workflow_status,
        'action': 'Review' if needs_review else 'View',
        'batch': {
            'code': batch_code,
            'name': batch_name,
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
            'start_date': report_date.isoformat(),
            'end_date': report_date.isoformat(),
        },
        'messages': messages,
        'flags': {
            'has_overdue': overdue_feeds > 0,
            'is_fully_automated': total_scheduled_feeds > 0 and disabled_feeds == 0,
        },
    }


def build_report_packets(start_date=None, end_date=None, batch_code=None, limit=50):
    now = timezone.now()
    queryset = Feeding.objects.select_related('batch_code')
    if batch_code:
        queryset = queryset.filter(batch_code__batch_code=batch_code)

    range_start, range_end = _date_bounds(start_date=start_date, end_date=end_date)
    if range_start:
        queryset = queryset.filter(feed_time__gte=range_start)
    if range_end:
        queryset = queryset.filter(feed_time__lt=range_end)

    grouped = defaultdict(list)
    for feeding in queryset.order_by('feed_time', 'feed_code'):
        local_date = timezone.localdate(timezone.localtime(feeding.feed_time))
        key = (feeding.batch_code.batch_code, feeding.batch_code.batch_name, local_date)
        grouped[key].append(feeding)

    packets = [
        _packet_from_group(batch, name, report_date, rows, now)
        for (batch, name, report_date), rows in grouped.items()
    ]
    packets.sort(key=lambda packet: (packet['date'], packet['batch']['code']), reverse=True)
    return packets[:limit]


def build_reports_summary(packets):
    reports_generated = len(packets)
    published = sum(1 for packet in packets if packet['workflow_status'] == 'published')
    draft_queue = sum(1 for packet in packets if packet['workflow_status'] == 'draft')
    needs_review = sum(1 for packet in packets if packet['status']['needs_review'])

    enabled_total = sum(packet['summary']['enabled_feeds'] for packet in packets)
    scheduled_total = sum(packet['summary']['total_scheduled_feeds'] for packet in packets)
    average_efficiency = round((enabled_total / scheduled_total) * 100) if scheduled_total else 0

    return {
        'reports_generated': reports_generated,
        'published': published,
        'scheduled_exports': 0,
        'draft_queue': draft_queue,
        'critical_findings': needs_review,
        'average_efficiency_percent': average_efficiency,
        'enabled_feeds': enabled_total,
        'total_scheduled_feeds': scheduled_total,
    }


def build_volume_trend(packets):
    totals_by_date = defaultdict(lambda: {'total_planned_feed_kg': 0.0, 'enabled_feeds': 0, 'disabled_feeds': 0})
    for packet in packets:
        date_key = packet['date']
        totals_by_date[date_key]['total_planned_feed_kg'] += packet['summary']['total_planned_feed_kg']
        totals_by_date[date_key]['enabled_feeds'] += packet['summary']['enabled_feeds']
        totals_by_date[date_key]['disabled_feeds'] += packet['summary']['disabled_feeds']

    series = []
    for date_key in sorted(totals_by_date.keys()):
        row = totals_by_date[date_key]
        series.append(
            {
                'date': date_key,
                'total_planned_feed_kg': round(row['total_planned_feed_kg'], 2),
                'enabled_feeds': row['enabled_feeds'],
                'disabled_feeds': row['disabled_feeds'],
            }
        )
    return series


def build_recent_activity(limit=10):
    now = timezone.now()
    feedings = (
        Feeding.objects.select_related('batch_code')
        .order_by('-feed_time', '-feed_code')[:limit]
    )
    activity = []
    for feeding in feedings:
        local_date = timezone.localdate(timezone.localtime(feeding.feed_time))
        report_id = _build_report_id(feeding.batch_code.batch_code, local_date)
        status = 'review' if feeding.feed_time < now else 'published'
        activity.append(
            {
                'report_id': report_id,
                'date': local_date.isoformat(),
                'owner': 'Admin',
                'status': status,
                'action': 'Review' if status == 'review' else 'View',
                'batch_code': feeding.batch_code.batch_code,
            }
        )
    return activity
