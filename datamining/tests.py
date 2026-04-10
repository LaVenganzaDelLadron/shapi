import csv
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from batch.models import PigBatches
from datamining.models import BatchPigMLSyncLog, PigMLData
from datamining.services import build_pig_ml_dataset, sync_batches_from_pigmldata_csv
from device.models import Device
from feeding.models import Feeding
from growth.models import GrowthStage
from pen.models import Pen
from record.models import Record


class PigMLDataBuilderTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.pen = Pen.objects.create(
            pen_name='North Pen',
            capacity=20,
            status='available',
            notes='test pen',
            date='2026-04-05T00:00:00Z',
        )
        self.growth_stage = GrowthStage.objects.create(
            growth_code='GROWTH001',
            growth_name='Grower',
            date='2026-04-05T00:00:00Z',
        )
        self.growth_stage_two = GrowthStage.objects.create(
            growth_code='GROWTH002',
            growth_name='Finisher',
            date='2026-04-05T00:00:00Z',
        )
        self.batch = PigBatches.objects.create(
            batch_name='Batch Alpha',
            no_of_pigs=10,
            current_age=54,
            avg_weight=20.4,
            notes='batch for datamining tests',
            pen_code=self.pen,
            growth_stage=self.growth_stage,
            date='2026-04-05T00:00:00Z',
        )
        self.device_one = Device.objects.create(
            pen_code=self.pen,
            date='2026-04-05T00:00:00Z',
        )
        self.device_two = Device.objects.create(
            pen_code=self.pen,
            date='2026-04-05T00:00:00Z',
        )
        self.record = Record.objects.create(
            batch_code=self.batch,
            pig_age_days=54,
            avg_weight=20.4,
            growth_stage=self.growth_stage,
            date='2026-04-05T12:00:00Z',
        )

        Feeding.objects.create(
            feed_quantity=10.0,
            feed_time='2026-04-04T05:00:00Z',
            repeat_days='Mon',
            feed_type='manual',
            growth_stage=self.growth_stage,
            batch_code=self.batch,
            device_code=self.device_one,
            pen_code=self.pen,
            date='2026-04-04T05:00:00Z',
        )
        Feeding.objects.create(
            feed_quantity=2.0,
            feed_time='2026-04-04T18:00:00Z',
            repeat_days='Thu',
            feed_type='automatic',
            growth_stage=self.growth_stage,
            batch_code=self.batch,
            device_code=self.device_one,
            pen_code=self.pen,
            date='2026-04-04T18:00:00Z',
        )
        Feeding.objects.create(
            feed_quantity=1.0,
            feed_time='2026-04-05T00:00:00Z',
            repeat_days='Fri',
            feed_type='manual',
            growth_stage=self.growth_stage,
            batch_code=self.batch,
            device_code=self.device_one,
            pen_code=self.pen,
            date='2026-04-05T00:00:00Z',
        )
        Feeding.objects.create(
            feed_quantity=3.0,
            feed_time='2026-04-05T06:00:00Z',
            repeat_days='Fri',
            feed_type='automatic',
            growth_stage=self.growth_stage,
            batch_code=self.batch,
            device_code=self.device_two,
            pen_code=self.pen,
            date='2026-04-05T06:00:00Z',
        )

    def test_build_dataset_uses_only_feedings_within_the_window(self):
        counts = build_pig_ml_dataset(window_days=1)

        row = PigMLData.objects.get(record=self.record)
        self.assertEqual(counts, {'processed': 1, 'created': 1, 'updated': 0})
        self.assertEqual(row.record_code, self.record.record_code)
        self.assertEqual(row.batch_code, self.batch.batch_code)
        self.assertEqual(row.pen_code, self.pen.pen_code)
        self.assertEqual(row.pen_status, 'available')
        self.assertEqual(row.feeding_count, 3)
        self.assertAlmostEqual(row.total_feed_quantity, 6.0)
        self.assertAlmostEqual(row.avg_feeding_interval_hours, 6.0)
        self.assertEqual(row.feed_type_mode, 'automatic')
        self.assertEqual(row.device_code, self.device_two.device_code)
        self.assertEqual(row.window_days, 1)

    def test_rebuild_preserves_snapshot_fields_by_default(self):
        build_pig_ml_dataset(window_days=1)

        Pen.objects.filter(pk=self.pen.pk).update(capacity=99, status='occupied')
        Record.objects.filter(pk=self.record.pk).update(
            avg_weight=22.1,
            growth_stage=self.growth_stage_two,
        )

        counts = build_pig_ml_dataset(window_days=1)

        row = PigMLData.objects.get(record=self.record)
        self.assertEqual(counts, {'processed': 1, 'created': 0, 'updated': 1})
        self.assertAlmostEqual(row.avg_weight, 22.1)
        self.assertEqual(row.pen_capacity, 20)
        self.assertEqual(row.pen_status, 'available')
        self.assertEqual(row.growth_stage, self.growth_stage.growth_code)
        self.assertEqual(PigMLData.objects.count(), 1)

    def test_rebuild_can_refresh_snapshot_fields_when_requested(self):
        build_pig_ml_dataset(window_days=1)

        Pen.objects.filter(pk=self.pen.pk).update(capacity=99, status='occupied')

        Record.objects.filter(pk=self.record.pk).update(growth_stage=self.growth_stage_two)

        build_pig_ml_dataset(window_days=1, refresh_snapshots=True)

        row = PigMLData.objects.get(record=self.record)
        self.assertEqual(row.pen_capacity, 99)
        self.assertEqual(row.pen_status, 'occupied')
        self.assertEqual(row.growth_stage, self.growth_stage_two.growth_code)

    def test_management_command_builds_dataset_and_read_api_returns_it(self):
        call_command('build_datamining_dataset', window_days=1)

        list_response = self.client.get(reverse('getAllPigMLData'))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertEqual(list_response.data['data'][0]['record_code'], self.record.record_code)

        detail_response = self.client.get(reverse('getPigMLData', args=[self.record.record_code]))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['data']['record_code'], self.record.record_code)


class BatchPigMLSyncTests(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / 'synthetic_pigmldata.csv'
        self.pen = Pen.objects.create(
            pen_name='Sync Pen',
            capacity=16,
            status='available',
            notes='pen for sync tests',
            date='2026-04-05T00:00:00Z',
        )
        self.starter = GrowthStage.objects.create(
            growth_code='GROWTH001',
            growth_name='STARTER',
            date='2026-04-05T00:00:00Z',
        )
        self.grower = GrowthStage.objects.create(
            growth_code='GROWTH002',
            growth_name='GROWER',
            date='2026-04-05T00:00:00Z',
        )
        self.finisher = GrowthStage.objects.create(
            growth_code='GROWTH003',
            growth_name='FINISHER',
            date='2026-04-05T00:00:00Z',
        )
        self.batch = PigBatches.objects.create(
            batch_code='BATCHSYNC001',
            batch_name='Sync Batch',
            no_of_pigs=12,
            current_age=60,
            avg_weight=24.5,
            notes='leave me unchanged',
            pen_code=self.pen,
            growth_stage=self.starter,
            date='2026-04-05T00:00:00Z',
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_csv(self, rows):
        fieldnames = [
            'record_code',
            'batch_code',
            'sample_date',
            'pig_age_days',
            'avg_weight',
            'total_feed_quantity',
            'feeding_count',
            'avg_feeding_interval_hours',
            'pen_code',
            'pen_capacity',
            'pen_status',
            'growth_stage',
            'feed_type_mode',
            'device_code',
            'window_days',
        ]
        with self.csv_path.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_csv_sync_uses_latest_row_only_and_logs_update(self):
        self._write_csv(
            [
                {
                    'record_code': 'REC001',
                    'batch_code': 'BATCHSYNC001',
                    'sample_date': '2026-04-09T08:00:00Z',
                    'pig_age_days': 63,
                    'avg_weight': 28.3,
                    'total_feed_quantity': 2.5,
                    'feeding_count': 4,
                    'avg_feeding_interval_hours': 6.0,
                    'pen_code': self.pen.pen_code,
                    'pen_capacity': 16,
                    'pen_status': 'available',
                    'growth_stage': 'GROWER',
                    'feed_type_mode': 'automatic',
                    'device_code': 'DEV001',
                    'window_days': 1,
                },
                {
                    'record_code': 'REC002',
                    'batch_code': 'BATCHSYNC001',
                    'sample_date': '2026-04-10T09:30:00Z',
                    'pig_age_days': 64,
                    'avg_weight': 29.7,
                    'total_feed_quantity': 2.8,
                    'feeding_count': 3,
                    'avg_feeding_interval_hours': 7.8,
                    'pen_code': self.pen.pen_code,
                    'pen_capacity': 16,
                    'pen_status': 'available',
                    'growth_stage': 'FINISHER',
                    'feed_type_mode': 'automatic',
                    'device_code': 'DEV001',
                    'window_days': 1,
                },
                {
                    'record_code': 'REC003',
                    'batch_code': 'UNKNOWNBATCH',
                    'sample_date': '2026-04-10T10:00:00Z',
                    'pig_age_days': 50,
                    'avg_weight': 20.0,
                    'total_feed_quantity': 1.5,
                    'feeding_count': 4,
                    'avg_feeding_interval_hours': 6.0,
                    'pen_code': 'PEN999',
                    'pen_capacity': 10,
                    'pen_status': 'available',
                    'growth_stage': 'STARTER',
                    'feed_type_mode': 'manual',
                    'device_code': 'DEV999',
                    'window_days': 1,
                },
            ]
        )

        counts = sync_batches_from_pigmldata_csv(csv_path=self.csv_path)

        self.batch.refresh_from_db()
        sync_log = BatchPigMLSyncLog.objects.get(batch=self.batch)

        self.assertEqual(
            counts,
            {
                'processed': 2,
                'updated': 1,
                'skipped': 0,
                'already_synced': 0,
                'missing_batches': 1,
                'missing_growth_stages': 0,
            },
        )
        self.assertEqual(self.batch.current_age, 64)
        self.assertAlmostEqual(self.batch.avg_weight, 29.7)
        self.assertEqual(self.batch.growth_stage, self.finisher)
        self.assertEqual(self.batch.no_of_pigs, 12)
        self.assertEqual(self.batch.pen_code, self.pen)
        self.assertEqual(self.batch.batch_name, 'Sync Batch')
        self.assertEqual(self.batch.notes, 'leave me unchanged')
        self.assertEqual(sync_log.old_age, 60)
        self.assertEqual(sync_log.new_age, 64)
        self.assertAlmostEqual(sync_log.old_avg_weight, 24.5)
        self.assertAlmostEqual(sync_log.new_avg_weight, 29.7)
        self.assertEqual(sync_log.old_growth_stage_code, self.starter.growth_code)
        self.assertEqual(sync_log.new_growth_stage_code, self.finisher.growth_code)

    def test_csv_sync_is_idempotent_when_rerun(self):
        self._write_csv(
            [
                {
                    'record_code': 'REC010',
                    'batch_code': 'BATCHSYNC001',
                    'sample_date': '2026-04-10T09:30:00Z',
                    'pig_age_days': 62,
                    'avg_weight': 28.1,
                    'total_feed_quantity': 2.2,
                    'feeding_count': 3,
                    'avg_feeding_interval_hours': 8.0,
                    'pen_code': self.pen.pen_code,
                    'pen_capacity': 16,
                    'pen_status': 'available',
                    'growth_stage': 'GROWER',
                    'feed_type_mode': 'automatic',
                    'device_code': 'DEV001',
                    'window_days': 1,
                },
            ]
        )

        first_counts = sync_batches_from_pigmldata_csv(csv_path=self.csv_path)
        second_counts = sync_batches_from_pigmldata_csv(csv_path=self.csv_path)

        self.batch.refresh_from_db()

        self.assertEqual(first_counts['updated'], 1)
        self.assertEqual(second_counts['updated'], 0)
        self.assertEqual(second_counts['already_synced'], 1)
        self.assertEqual(BatchPigMLSyncLog.objects.filter(batch=self.batch).count(), 1)
        self.assertEqual(self.batch.current_age, 62)
        self.assertAlmostEqual(self.batch.avg_weight, 28.1)
        self.assertEqual(self.batch.growth_stage, self.grower)

    def test_management_command_syncs_batches_from_csv(self):
        self._write_csv(
            [
                {
                    'record_code': 'REC020',
                    'batch_code': 'BATCHSYNC001',
                    'sample_date': '2026-04-10T15:00:00Z',
                    'pig_age_days': 66,
                    'avg_weight': 31.2,
                    'total_feed_quantity': 2.9,
                    'feeding_count': 3,
                    'avg_feeding_interval_hours': 7.8,
                    'pen_code': self.pen.pen_code,
                    'pen_capacity': 16,
                    'pen_status': 'available',
                    'growth_stage': 'FINISHER',
                    'feed_type_mode': 'automatic',
                    'device_code': 'DEV001',
                    'window_days': 1,
                },
            ]
        )

        call_command('sync_batches_from_pigmldata', csv_path=str(self.csv_path))

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.current_age, 66)
        self.assertAlmostEqual(self.batch.avg_weight, 31.2)
        self.assertEqual(self.batch.growth_stage, self.finisher)
