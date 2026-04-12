from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from batch.models import PigBatches
from growth.models import GrowthStage
from pen.models import Pen
from record.models import Record


class DashboardGrowthTrendsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.pen = Pen.objects.create(
            pen_name='Dashboard Pen',
            capacity=10,
            status='available',
            notes='dashboard pen',
            date=timezone.now(),
        )
        self.growth_stage = GrowthStage.objects.create(
            growth_name='Grower',
            date=timezone.now(),
        )
        self.batch = PigBatches.objects.create(
            batch_name='Dashboard Batch',
            no_of_pigs=5,
            current_age=0,
            avg_weight=14.5,
            notes='dashboard batch',
            pen_code=self.pen,
            growth_stage=self.growth_stage,
            date=timezone.now() - timedelta(days=12),
        )

    def test_growth_trends_reads_from_snapshot_records(self):
        first_snapshot = timezone.now() - timedelta(days=2)
        second_snapshot = timezone.now() - timedelta(days=1)
        Record.objects.create(
            batch_code=self.batch,
            pig_age_days=10,
            avg_weight=14.5,
            growth_stage=self.growth_stage,
            date=first_snapshot,
        )
        Record.objects.create(
            batch_code=self.batch,
            pig_age_days=11,
            avg_weight=15.2,
            growth_stage=self.growth_stage,
            date=second_snapshot,
        )

        response = self.client.get(reverse('dashboardGrowthTrends'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['batch_code'], self.batch.batch_code)
        self.assertEqual(len(response.data['results'][0]['series']), 2)
