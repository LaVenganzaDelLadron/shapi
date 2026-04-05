from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from batch.models import PigBatches
from datamining.models import PigMLData
from datamining.services import build_pig_ml_dataset
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
