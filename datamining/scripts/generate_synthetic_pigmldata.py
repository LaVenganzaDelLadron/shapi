import argparse
import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


GROWTH_STAGES = ('HOGPRE', 'STARTER', 'GROWER', 'FINISHER')
FEED_TYPES = ('manual', 'automatic')
WINDOW_CHOICES = (1, 1, 1, 7)


def _build_row(record_index, batch_index, batch, sample_date, pig_age_days, randomizer):
    if pig_age_days <= 44:
        growth_stage = 'HOGPRE'
        feeding_count = randomizer.choice((4, 4, 5))
        total_feed_quantity = round(randomizer.uniform(1.1, 1.8), 2)
        weight_base = 7 + (pig_age_days - 30) * 0.38
    elif pig_age_days <= 69:
        growth_stage = 'STARTER'
        feeding_count = randomizer.choice((3, 4, 4))
        total_feed_quantity = round(randomizer.uniform(1.7, 2.6), 2)
        weight_base = 12.5 + (pig_age_days - 45) * 0.62
    elif pig_age_days <= 109:
        growth_stage = 'GROWER'
        feeding_count = randomizer.choice((3, 3, 4))
        total_feed_quantity = round(randomizer.uniform(2.4, 3.4), 2)
        weight_base = 28 + (pig_age_days - 70) * 0.95
    else:
        growth_stage = 'FINISHER'
        feeding_count = randomizer.choice((2, 3, 3))
        total_feed_quantity = round(randomizer.uniform(3.1, 4.2), 2)
        weight_base = 66 + (pig_age_days - 110) * 1.08

    batch_effect = (batch_index % 5 - 2) * 0.8
    noise = randomizer.uniform(-1.8, 1.8)
    avg_weight = round(max(6.5, weight_base + batch_effect + noise), 1)

    if feeding_count == 5:
        avg_feeding_interval_hours = round(randomizer.uniform(4.3, 5.2), 1)
    elif feeding_count == 4:
        avg_feeding_interval_hours = round(randomizer.uniform(5.4, 6.6), 1)
    elif feeding_count == 3:
        avg_feeding_interval_hours = round(randomizer.uniform(7.4, 8.8), 1)
    else:
        avg_feeding_interval_hours = round(randomizer.uniform(10.8, 12.4), 1)

    return {
        'record_code': f'SYNREC{record_index:03d}',
        'batch_code': batch['batch_code'],
        'sample_date': sample_date.isoformat().replace('+00:00', 'Z'),
        'pig_age_days': pig_age_days,
        'avg_weight': avg_weight,
        'total_feed_quantity': total_feed_quantity,
        'feeding_count': feeding_count,
        'avg_feeding_interval_hours': avg_feeding_interval_hours,
        'pen_code': batch['pen_code'],
        'pen_capacity': batch['pen_capacity'],
        'pen_status': batch['pen_status'],
        'growth_stage': growth_stage,
        'feed_type_mode': batch['feed_type_mode'],
        'device_code': batch['device_code'],
        'window_days': randomizer.choice(WINDOW_CHOICES),
    }


def generate_dataset(row_count=120, seed=42):
    if row_count < 100 or row_count > 300:
        raise ValueError('row_count must be between 100 and 300.')

    randomizer = random.Random(seed)
    batch_count = max(20, row_count // 5)
    batch_count = min(batch_count, row_count)
    rows_per_batch = row_count // batch_count
    extra_rows = row_count % batch_count

    pens = []
    batches = []
    for index in range(1, batch_count + 1):
        pen_capacity = randomizer.randint(10, 30)
        occupancy = randomizer.randint(max(8, pen_capacity - 4), pen_capacity + 3)
        pen_status = 'occupied' if occupancy >= pen_capacity else 'available'
        feed_type_mode = randomizer.choice(FEED_TYPES)
        pen = {
            'pen_code': f'SYNPEN{index:03d}',
            'pen_capacity': pen_capacity,
            'pen_status': pen_status,
            'feed_type_mode': feed_type_mode,
            'device_code': f'SYNDEV{index:03d}',
        }
        pens.append(pen)
        batches.append(
            {
                'batch_code': f'SYNBATCH{index:03d}',
                'pen_code': pen['pen_code'],
                'pen_capacity': pen['pen_capacity'],
                'pen_status': pen['pen_status'],
                'feed_type_mode': pen['feed_type_mode'],
                'device_code': pen['device_code'],
            }
        )

    base_date = datetime(2026, 4, 7, 8, 0, tzinfo=timezone.utc)
    rows = []
    record_index = 1

    for batch_index, batch in enumerate(batches, start=1):
        row_total = rows_per_batch + (1 if batch_index <= extra_rows else 0)
        start_age = randomizer.randint(30, 120)
        max_increment = max(1, min(30, 150 - start_age))
        increments = sorted(randomizer.sample(range(0, max_increment + 1), row_total))

        for offset, increment in enumerate(increments):
            pig_age_days = start_age + increment
            sample_date = base_date - timedelta(
                days=(row_count - record_index) % 27,
                hours=(offset * 3 + batch_index) % 10,
            )
            rows.append(_build_row(record_index, batch_index, batch, sample_date, pig_age_days, randomizer))
            record_index += 1

    return rows


def write_outputs(rows, json_path, csv_path):
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with json_path.open('w', encoding='utf-8') as json_file:
        json.dump(rows, json_file, indent=2)

    with csv_path.open('w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description='Generate synthetic SmartHog PigMLData rows as JSON and CSV.')
    parser.add_argument('--rows', type=int, default=120, help='Number of rows to generate (100-300).')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for deterministic generation.')
    parser.add_argument(
        '--output-dir',
        default='datamining/generated',
        help='Directory where the JSON and CSV files will be written.',
    )
    args = parser.parse_args()

    rows = generate_dataset(row_count=args.rows, seed=args.seed)
    output_dir = Path(args.output_dir)
    json_path = output_dir / 'synthetic_pigmldata.json'
    csv_path = output_dir / 'synthetic_pigmldata.csv'
    write_outputs(rows, json_path, csv_path)

    print(json.dumps({'rows': len(rows), 'json_path': str(json_path), 'csv_path': str(csv_path)}))


if __name__ == '__main__':
    main()
