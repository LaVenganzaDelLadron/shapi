from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from batch.models import PigBatches
from device.models import Device
from feeding.models import Feeding
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
        self.device = Device.objects.create(
            pen_code=self.pen,
            date=timezone.now(),
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

    def test_api_dashboard_routes_return_structured_json(self):
        sample_time = timezone.now() - timedelta(hours=2)
        Record.objects.create(
            batch_code=self.batch,
            pig_age_days=12,
            avg_weight=16.0,
            growth_stage=self.growth_stage,
            date=sample_time,
        )
        Feeding.objects.create(
            feed_quantity=3.25,
            feed_time=sample_time,
            repeat_days='everyday',
            feed_type='automatic',
            growth_stage=self.growth_stage,
            batch_code=self.batch,
            device_code=self.device,
            pen_code=self.pen,
            date=sample_time,
        )

        overview_response = self.client.get('/api/dashboard/overview/')
        trends_response = self.client.get('/api/dashboard/growth-trends/')
        feed_response = self.client.get('/api/dashboard/feed-consumption/')

        self.assertEqual(overview_response.status_code, status.HTTP_200_OK)
        self.assertEqual(overview_response.data['status'], 'success')
        self.assertIn('total_pigs', overview_response.data['results'])

        self.assertEqual(trends_response.status_code, status.HTTP_200_OK)
        self.assertEqual(trends_response.data['status'], 'success')
        self.assertEqual(trends_response.data['results'][0]['batch_code'], self.batch.batch_code)

        self.assertEqual(feed_response.status_code, status.HTTP_200_OK)
        self.assertEqual(feed_response.data['status'], 'success')
        self.assertEqual(feed_response.data['results'][0]['batch_code'], self.batch.batch_code)
