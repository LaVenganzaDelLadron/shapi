from django.db import transaction

from batch.age import calculate_batch_age, ensure_aware_utc, utc_date
from batch.models import PigBatches
from record.models import Record


def create_daily_snapshot_records(snapshot_at=None):
    snapshot_at = ensure_aware_utc(snapshot_at)
    snapshot_day = utc_date(snapshot_at)

    active_batches = list(
        PigBatches.objects.select_related('growth_stage')
        .filter(no_of_pigs__gt=0)
        .order_by('batch_code')
    )
    if not active_batches:
        return {
            'processed': 0,
            'created': 0,
            'skipped': 0,
            'snapshot_day': snapshot_day.isoformat(),
        }

    existing_batch_ids = set(
        Record.objects.filter(
            batch_code_id__in=[batch.id for batch in active_batches],
            date__date=snapshot_day,
        ).values_list('batch_code_id', flat=True)
    )

    counts = {
        'processed': len(active_batches),
        'created': 0,
        'skipped': 0,
        'snapshot_day': snapshot_day.isoformat(),
    }

    with transaction.atomic():
        for batch in active_batches:
            if batch.id in existing_batch_ids:
                counts['skipped'] += 1
                continue

            Record.objects.create(
                batch_code=batch,
                pig_age_days=calculate_batch_age(batch.date, as_of=snapshot_at),
                avg_weight=batch.avg_weight,
                growth_stage=batch.growth_stage,
                date=snapshot_at,
            )
            counts['created'] += 1

    return counts
