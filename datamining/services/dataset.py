import csv
import logging
from collections import defaultdict, deque
from datetime import timedelta
from pathlib import Path

from django.db import transaction
from django.utils.dateparse import parse_datetime

from batch.models import PigBatches
from datamining.models import BatchPigMLSyncLog, PigMLData
from feeding.models import Feeding
from growth.models import GrowthStage
from record.models import Record


logger = logging.getLogger(__name__)


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


def _normalize_growth_value(value):
    return ''.join(character for character in str(value or '').upper() if character.isalnum())


def _parse_csv_datetime(value):
    parsed = parse_datetime(str(value or '').strip())
    if parsed is None:
        raise ValueError(f'Invalid sample_date value: {value!r}')
    return parsed


def _load_latest_csv_rows(csv_path):
    latest_rows = {}

    with Path(csv_path).open('r', encoding='utf-8', newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        required_fields = {'batch_code', 'sample_date', 'pig_age_days', 'avg_weight', 'growth_stage'}
        if not required_fields.issubset(set(reader.fieldnames or [])):
            raise ValueError(
                'CSV file must include the following columns: {}'.format(', '.join(sorted(required_fields)))
            )

        for row in reader:
            batch_code = str(row.get('batch_code', '')).strip()
            if not batch_code:
                continue

            sample_date = _parse_csv_datetime(row.get('sample_date'))
            normalized_row = {
                'batch_code': batch_code,
                'sample_date': sample_date,
                'pig_age_days': int(float(row['pig_age_days'])),
                'avg_weight': float(row['avg_weight']),
                'growth_stage': str(row.get('growth_stage', '')).strip(),
            }

            current_latest = latest_rows.get(batch_code)
            if current_latest is None or sample_date >= current_latest['sample_date']:
                latest_rows[batch_code] = normalized_row

    return latest_rows


def _build_growth_stage_lookup():
    lookup = {}
    for growth_stage in GrowthStage.objects.all():
        lookup[_normalize_growth_value(growth_stage.growth_code)] = growth_stage
        lookup[_normalize_growth_value(growth_stage.growth_name)] = growth_stage
    return lookup


def sync_batches_from_pigmldata_csv(csv_path='datamining/generated/synthetic_pigmldata.csv'):
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f'Pig ML CSV file not found: {csv_file}')

    latest_rows = _load_latest_csv_rows(csv_file)
    if not latest_rows:
        return {
            'processed': 0,
            'updated': 0,
            'skipped': 0,
            'already_synced': 0,
            'missing_batches': 0,
            'missing_growth_stages': 0,
        }

    batch_codes = sorted(latest_rows.keys())
    batches = PigBatches.objects.select_related('growth_stage').filter(batch_code__in=batch_codes)
    batches_by_code = {batch.batch_code: batch for batch in batches}
    growth_stage_lookup = _build_growth_stage_lookup()
    existing_logs = set(
        BatchPigMLSyncLog.objects.filter(batch__batch_code__in=batch_codes).values_list(
            'batch__batch_code',
            'source_sample_date',
        )
    )

    counts = {
        'processed': 0,
        'updated': 0,
        'skipped': 0,
        'already_synced': 0,
        'missing_batches': 0,
        'missing_growth_stages': 0,
    }

    for batch_code in batch_codes:
        counts['processed'] += 1
        row = latest_rows[batch_code]
        batch = batches_by_code.get(batch_code)
        if not batch:
            counts['missing_batches'] += 1
            logger.warning('Skipping CSV sync for unknown batch_code=%s', batch_code)
            continue

        log_key = (batch_code, row['sample_date'])
        if log_key in existing_logs:
            counts['already_synced'] += 1
            logger.info(
                'Skipping batch_code=%s because sample_date=%s was already synced',
                batch_code,
                row['sample_date'].isoformat(),
            )
            continue

        growth_stage_value = row['growth_stage']
        growth_stage = growth_stage_lookup.get(_normalize_growth_value(growth_stage_value))
        if not growth_stage:
            counts['missing_growth_stages'] += 1
            logger.warning(
                'Skipping batch_code=%s because growth_stage=%s could not be mapped',
                batch_code,
                growth_stage_value,
            )
            continue

        old_age = batch.current_age
        old_weight = batch.avg_weight
        old_growth_stage_code = batch.growth_stage.growth_code

        new_age = row['pig_age_days']
        new_weight = row['avg_weight']
        new_growth_stage_code = growth_stage.growth_code

        if (
            old_age == new_age
            and round(old_weight, 6) == round(new_weight, 6)
            and old_growth_stage_code == new_growth_stage_code
        ):
            counts['skipped'] += 1
            logger.info(
                'Skipping batch_code=%s because CSV latest row does not change tracked fields',
                batch_code,
            )
            continue

        with transaction.atomic():
            PigBatches.objects.filter(pk=batch.pk).update(
                current_age=new_age,
                avg_weight=new_weight,
                growth_stage_id=growth_stage.pk,
            )
            BatchPigMLSyncLog.objects.create(
                batch=batch,
                batch_code=batch_code,
                source_sample_date=row['sample_date'],
                old_age=old_age,
                new_age=new_age,
                old_avg_weight=old_weight,
                new_avg_weight=new_weight,
                old_growth_stage_code=old_growth_stage_code,
                new_growth_stage_code=new_growth_stage_code,
            )

        counts['updated'] += 1
        existing_logs.add(log_key)
        logger.info(
            'Updated batch_code=%s age %s->%s weight %.2f->%.2f growth_stage %s->%s at %s',
            batch_code,
            old_age,
            new_age,
            old_weight,
            new_weight,
            old_growth_stage_code,
            new_growth_stage_code,
            row['sample_date'].isoformat(),
        )

    return counts


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
