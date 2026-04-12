import logging
from collections import defaultdict
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from batch.age import calculate_batch_age
from batch.models import PigBatches
from datamining.models import BatchPigMLSyncLog, PigMLData


logger = logging.getLogger(__name__)


def _validate_rolling_window(rolling_window):
    if rolling_window < 1 or rolling_window > 5:
        raise ValueError('rolling_window must be between 1 and 5.')


def _calculate_smoothed_weight(rows, rolling_window):
    recent_rows = rows[-rolling_window:]
    return round(sum(row.avg_weight for row in recent_rows) / len(recent_rows), 2)


def _build_dashboard_summary(batch, latest_row, rows, summary_date):
    today_rows = [
        row
        for row in rows
        if timezone.localdate(timezone.localtime(row.sample_date)) == summary_date
    ]
    total_feed_today = round(sum(row.total_feed_quantity for row in today_rows), 2)
    feeding_count_today = int(sum(row.feeding_count for row in today_rows))

    next_feeding_time = None
    if latest_row.avg_feeding_interval_hours > 0:
        next_feeding_time = latest_row.sample_date + timedelta(hours=float(latest_row.avg_feeding_interval_hours))

    return {
        'batch_code': batch.batch_code,
        'current_age': batch.get_current_age(),
        'avg_weight': round(float(batch.avg_weight), 2),
        'total_feed_today': total_feed_today,
        'feeding_count_today': feeding_count_today,
        'next_feeding_time': next_feeding_time.isoformat() if next_feeding_time else None,
    }


def update_batches_daily_from_dataset(rolling_window=3, summary_date=None):
    _validate_rolling_window(rolling_window)

    summary_date = summary_date or timezone.localdate()
    dataset_rows = list(
        PigMLData.objects.all().order_by('batch_code', 'sample_date', 'record_code')
    )
    if not dataset_rows:
        return {
            'processed': 0,
            'updated': 0,
            'skipped': 0,
            'already_synced': 0,
            'missing_batches': 0,
            'data': [],
        }

    rows_by_batch = defaultdict(list)
    for row in dataset_rows:
        rows_by_batch[row.batch_code].append(row)

    batches = PigBatches.objects.filter(batch_code__in=rows_by_batch.keys())
    batches_by_code = {batch.batch_code: batch for batch in batches}
    existing_logs = {
        (batch_code, source_sample_date): log_id
        for log_id, batch_code, source_sample_date in BatchPigMLSyncLog.objects.filter(
            batch__batch_code__in=rows_by_batch.keys()
        ).values_list('id', 'batch__batch_code', 'source_sample_date')
    }

    counts = {
        'processed': 0,
        'updated': 0,
        'skipped': 0,
        'already_synced': 0,
        'missing_batches': 0,
    }
    summaries = []

    for batch_code in sorted(rows_by_batch.keys()):
        counts['processed'] += 1
        rows = rows_by_batch[batch_code]
        batch = batches_by_code.get(batch_code)
        if not batch:
            counts['missing_batches'] += 1
            logger.warning('Ignoring orphan PigMLData row for unknown batch_code=%s', batch_code)
            continue

        latest_row = rows[-1]
        target_age = calculate_batch_age(batch.date)
        target_weight = _calculate_smoothed_weight(rows, rolling_window)
        log_key = (batch_code, latest_row.sample_date)
        has_existing_log = log_key in existing_logs
        batch_is_current = (
            batch.current_age == target_age
            and round(float(batch.avg_weight), 6) == round(float(target_weight), 6)
        )

        if has_existing_log and batch_is_current:
            counts['already_synced'] += 1
            summaries.append(_build_dashboard_summary(batch, latest_row, rows, summary_date))
            continue

        old_age = batch.current_age
        old_weight = float(batch.avg_weight)
        growth_stage_code = batch.growth_stage.growth_code if batch.growth_stage_id else ''

        if batch_is_current:
            counts['skipped'] += 1
            BatchPigMLSyncLog.objects.get_or_create(
                batch=batch,
                source_sample_date=latest_row.sample_date,
                defaults={
                    'batch_code': batch_code,
                    'old_age': old_age,
                    'new_age': target_age,
                    'old_avg_weight': old_weight,
                    'new_avg_weight': target_weight,
                    'old_growth_stage_code': growth_stage_code,
                    'new_growth_stage_code': growth_stage_code,
                },
            )
            logger.info(
                'No batch field change needed for batch_code=%s at sample_date=%s',
                batch_code,
                latest_row.sample_date.isoformat(),
            )
        else:
            with transaction.atomic():
                PigBatches.objects.filter(pk=batch.pk).update(
                    current_age=target_age,
                    avg_weight=target_weight,
                )
                BatchPigMLSyncLog.objects.get_or_create(
                    batch=batch,
                    source_sample_date=latest_row.sample_date,
                    defaults={
                        'batch_code': batch_code,
                        'old_age': old_age,
                        'new_age': target_age,
                        'old_avg_weight': old_weight,
                        'new_avg_weight': target_weight,
                        'old_growth_stage_code': growth_stage_code,
                        'new_growth_stage_code': growth_stage_code,
                    },
                )

            batch.current_age = target_age
            batch.avg_weight = target_weight
            counts['updated'] += 1
            logger.info(
                'Updated batch_code=%s age %s->%s weight %.2f->%.2f at %s',
                batch_code,
                old_age,
                target_age,
                old_weight,
                target_weight,
                timezone.now().isoformat(),
            )

        existing_logs[log_key] = True
        summaries.append(_build_dashboard_summary(batch, latest_row, rows, summary_date))

    return {
        **counts,
        'data': summaries,
    }
