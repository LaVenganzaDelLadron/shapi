from collections import defaultdict, deque
from datetime import timedelta

from django.db import transaction

from datamining.models import PigMLData
from feeding.models import Feeding
from record.models import Record


def _average_interval_hours(feedings):
    if len(feedings) < 2:
        return 0.0

    total_hours = 0.0
    for previous, current in zip(feedings, feedings[1:]):
        total_hours += (current.feed_time - previous.feed_time).total_seconds() / 3600

    return total_hours / (len(feedings) - 1)


def _feed_type_mode(feedings):
    if not feedings:
        return ''

    counts = defaultdict(int)
    latest_seen = {}
    for feeding in feedings:
        counts[feeding.feed_type] += 1
        latest_seen[feeding.feed_type] = feeding.feed_time

    return sorted(
        counts,
        key=lambda feed_type: (-counts[feed_type], -latest_seen[feed_type].timestamp(), feed_type),
    )[0]


def _build_row_payload(record, window_feedings, window_days):
    pen = record.batch_code.pen_code
    latest_device_code = ''
    if window_feedings:
        latest_device_code = window_feedings[-1].device_code.device_code

    return {
        'record_code': record.record_code,
        'batch_code': record.batch_code.batch_code,
        'pen_code': pen.pen_code,
        'sample_date': record.date,
        'pig_age_days': record.pig_age_days,
        'avg_weight': record.avg_weight,
        'total_feed_quantity': sum(feeding.feed_quantity for feeding in window_feedings),
        'feeding_count': len(window_feedings),
        'avg_feeding_interval_hours': _average_interval_hours(window_feedings),
        'pen_capacity': pen.capacity,
        'pen_status': pen.status,
        'growth_stage': record.growth_stage.growth_code,
        'feed_type_mode': _feed_type_mode(window_feedings),
        'device_code': latest_device_code,
        'window_days': window_days,
    }


def build_pig_ml_dataset(window_days=1, refresh_snapshots=False):
    if window_days <= 0:
        raise ValueError('window_days must be greater than zero.')

    records = list(
        Record.objects.select_related(
            'batch_code__pen_code',
            'growth_stage',
        ).order_by('batch_code_id', 'date', 'record_code')
    )

    if not records:
        return {'processed': 0, 'created': 0, 'updated': 0}

    records_by_batch = defaultdict(list)
    for record in records:
        records_by_batch[record.batch_code_id].append(record)

    feedings_by_batch = defaultdict(list)
    batch_ids = list(records_by_batch.keys())
    feedings = Feeding.objects.filter(batch_code_id__in=batch_ids).select_related('device_code').order_by(
        'batch_code_id',
        'feed_time',
        'feed_code',
    )
    for feeding in feedings:
        feedings_by_batch[feeding.batch_code_id].append(feeding)

    counts = {'processed': 0, 'created': 0, 'updated': 0}
    snapshot_fields = ['batch_code', 'pen_code', 'pen_capacity', 'pen_status', 'growth_stage']
    recomputed_fields = [
        'record_code',
        'sample_date',
        'pig_age_days',
        'avg_weight',
        'total_feed_quantity',
        'feeding_count',
        'avg_feeding_interval_hours',
        'feed_type_mode',
        'device_code',
        'window_days',
    ]

    with transaction.atomic():
        for batch_id, batch_records in records_by_batch.items():
            batch_feedings = feedings_by_batch[batch_id]
            window_feedings = deque()
            feed_index = 0

            for record in batch_records:
                while feed_index < len(batch_feedings) and batch_feedings[feed_index].feed_time <= record.date:
                    window_feedings.append(batch_feedings[feed_index])
                    feed_index += 1

                window_start = record.date - timedelta(days=window_days)
                while window_feedings and window_feedings[0].feed_time < window_start:
                    window_feedings.popleft()

                payload = _build_row_payload(record, list(window_feedings), window_days)
                dataset_row, created = PigMLData.objects.get_or_create(
                    record=record,
                    defaults=payload,
                )

                if created:
                    counts['created'] += 1
                else:
                    update_fields = list(recomputed_fields)
                    if refresh_snapshots:
                        update_fields.extend(snapshot_fields)

                    for field_name in update_fields:
                        setattr(dataset_row, field_name, payload[field_name])
                    dataset_row.save(update_fields=update_fields + ['updated_at'])
                    counts['updated'] += 1

                counts['processed'] += 1

    return counts
