from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from batch.models import PigBatches
from growth.models import GrowthStage
from pen.models import Pen
from record.models import Record


class RecordControllerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.batch_start = timezone.now() - timedelta(days=20)
        self.pen = Pen.objects.create(
            pen_name='North Pen',
            capacity=20,
            status='available',
            notes='test pen',
            date=self.batch_start,
        )
        self.growth_stage = GrowthStage.objects.create(
            growth_name='Grower',
            date=self.batch_start,
        )
        self.batch = PigBatches.objects.create(
            batch_name='Batch Alpha',
            no_of_pigs=10,
            current_age=99,
            avg_weight=22.5,
            notes='test batch',
            pen_code=self.pen,
            growth_stage=self.growth_stage,
            date=self.batch_start,
        )

    def test_post_duplicate_record_returns_already_exists_for_same_utc_day(self):
        snapshot_time = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        payload = {
            'batch_code': self.batch.batch_code,
            'avg_weight': 22.5,
            'growth_stage': self.growth_stage.growth_code,
            'date': snapshot_time.isoformat(),
        }
        duplicate_payload = {
            **payload,
            'avg_weight': 23.1,
            'date': (snapshot_time + timedelta(hours=4)).isoformat(),
        }

        first_response = self.client.post(reverse('addRecord'), payload, format='json')
        second_response = self.client.post(reverse('addRecord'), duplicate_payload, format='json')

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            second_response.data,
            {'message': 'A daily snapshot already exists for this batch on this UTC day.'},
        )
        self.assertEqual(Record.objects.count(), 1)

    def test_post_computes_pig_age_days_from_batch_start_date(self):
        snapshot_time = timezone.now().replace(hour=6, minute=0, second=0, microsecond=0)
        response = self.client.post(
            reverse('addRecord'),
            {
                'batch_code': self.batch.batch_code,
                'avg_weight': 22.5,
                'growth_stage': self.growth_stage.growth_code,
                'date': snapshot_time.isoformat(),
            },
            format='json',
        )

        record = Record.objects.get()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            record.pig_age_days,
            (snapshot_time.date() - self.batch_start.date()).days,
        )

    def test_update_endpoint_rejects_mutating_existing_record(self):
        record = Record.objects.create(
            batch_code=self.batch,
            pig_age_days=20,
            avg_weight=22.5,
            growth_stage=self.growth_stage,
            date=timezone.now(),
        )

        response = self.client.patch(
            reverse('updateRecord', args=[record.record_code]),
            {'avg_weight': 30.0},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(
            response.data,
            {'message': 'Historical records are immutable. Create a new snapshot instead.'},
        )

    def test_daily_snapshot_command_creates_one_record_per_active_batch(self):
        call_command('create_daily_batch_snapshots')
        call_command('create_daily_batch_snapshots')

        record = Record.objects.get(batch_code=self.batch)

        self.assertEqual(Record.objects.count(), 1)
        self.assertEqual(record.avg_weight, self.batch.avg_weight)
        self.assertEqual(record.growth_stage, self.batch.growth_stage)
