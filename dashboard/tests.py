from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from batch.models import PigBatches
from datamining.models import PigMLData
from device.models import Device
from feeding.models import Feeding
from growth.models import GrowthStage
from pen.models import Pen
from record.models import Record


class DashboardBaseTestCase(TestCase):
    def setUp(self):
        super().setUp()
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

    def create_record(self, sample_time, pig_age_days, avg_weight):
        return Record.objects.create(
            batch_code=self.batch,
            pig_age_days=pig_age_days,
            avg_weight=avg_weight,
            growth_stage=self.growth_stage,
            date=sample_time,
        )

    def create_feeding(
        self,
        sample_time,
        feed_quantity=3.25,
        repeat_days='everyday',
        feed_type='automatic',
    ):
        return Feeding.objects.create(
            feed_quantity=feed_quantity,
            feed_time=sample_time,
            repeat_days=repeat_days,
            feed_type=feed_type,
            growth_stage=self.growth_stage,
            batch_code=self.batch,
            device_code=self.device,
            pen_code=self.pen,
            date=sample_time,
        )

    def create_pig_ml_data(self, record, avg_feeding_interval_hours):
        return PigMLData.objects.create(
            record=record,
            record_code=record.record_code,
            batch_code=self.batch.batch_code,
            pen_code=self.pen.pen_code,
            sample_date=record.date,
            pig_age_days=record.pig_age_days,
            avg_weight=record.avg_weight,
            total_feed_quantity=3.25,
            feeding_count=1,
            avg_feeding_interval_hours=avg_feeding_interval_hours,
            pen_capacity=self.pen.capacity,
            pen_status=self.pen.status,
            growth_stage=self.growth_stage.growth_name,
            feed_type_mode='automatic',
            device_code=self.device.device_code,
        )


class DashboardGrowthTrendsTests(DashboardBaseTestCase):
    def test_growth_trends_reads_from_snapshot_records(self):
        first_snapshot = timezone.now() - timedelta(days=2)
        second_snapshot = timezone.now() - timedelta(days=1)
        self.create_record(first_snapshot, pig_age_days=10, avg_weight=14.5)
        self.create_record(second_snapshot, pig_age_days=11, avg_weight=15.2)

        response = self.client.get(reverse('dashboardGrowthTrends'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['batch_code'], self.batch.batch_code)
        self.assertEqual(len(response.data['results'][0]['series']), 3)

    def test_growth_trends_appends_live_batch_snapshot(self):
        first_snapshot = timezone.now() - timedelta(days=2)
        self.create_record(first_snapshot, pig_age_days=10, avg_weight=14.5)

        response = self.client.get(reverse('dashboardGrowthTrends'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(len(response.data['results']), 1)

        series = response.data['results'][0]['series']
        self.assertEqual(len(series), 2)
        self.assertEqual(series[0]['avg_weight'], 14.5)
        self.assertEqual(series[1]['avg_weight'], self.batch.avg_weight)

        live_sample_date = datetime.fromisoformat(series[1]['sample_date'])
        self.assertEqual(live_sample_date.date(), timezone.localdate())
        self.assertEqual(series[1]['pig_age_days'], self.batch.get_current_age())

    def test_growth_trends_rejects_invalid_date_range(self):
        response = self.client.get(
            reverse('dashboardGrowthTrends'),
            {
                'start_date': '2026-04-10',
                'end_date': '2026-04-09',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'error')
        self.assertIn('start_date must be on or before end_date.', response.data['message'])

    def test_api_dashboard_routes_return_structured_json(self):
        sample_time = timezone.now() - timedelta(hours=2)
        self.create_record(sample_time, pig_age_days=12, avg_weight=16.0)
        self.create_feeding(sample_time)

        overview_response = self.client.get(reverse('dashboardOverview'))
        trends_response = self.client.get(reverse('dashboardGrowthTrends'))
        feed_response = self.client.get(reverse('dashboardFeedConsumption'))

        self.assertEqual(overview_response.status_code, status.HTTP_200_OK)
        self.assertEqual(overview_response.data['status'], 'success')
        self.assertIn('total_pigs', overview_response.data['results'])

        self.assertEqual(trends_response.status_code, status.HTTP_200_OK)
        self.assertEqual(trends_response.data['status'], 'success')
        self.assertEqual(trends_response.data['results'][0]['batch_code'], self.batch.batch_code)

        self.assertEqual(feed_response.status_code, status.HTTP_200_OK)
        self.assertEqual(feed_response.data['status'], 'success')
        self.assertEqual(feed_response.data['results'][0]['batch_code'], self.batch.batch_code)

    def test_next_feeding_schedule_returns_predicted_next_feed_time(self):
        sample_time = timezone.now() - timedelta(hours=2)
        record = self.create_record(sample_time, pig_age_days=12, avg_weight=16.0)
        self.create_feeding(sample_time, repeat_days='everyday')
        self.create_pig_ml_data(record, avg_feeding_interval_hours=6)

        response = self.client.get(reverse('dashboardNextFeedingSchedule'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['batch_code'], self.batch.batch_code)
        self.assertIsNotNone(response.data['results'][0]['next_feeding_time'])

    def test_feed_dispensed_today_supports_per_batch_breakdown(self):
        sample_time = timezone.now() - timedelta(hours=1)
        self.create_feeding(sample_time, feed_quantity=4.5)

        response = self.client.get(
            reverse('dashboardFeedDispensedToday'),
            {
                'per_batch': True,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['results'][0]['batch_code'], self.batch.batch_code)
        self.assertEqual(response.data['results'][0]['total_feed_quantity'], 4.5)

    def test_report_preview_returns_structured_frontend_ready_payload(self):
        now = timezone.now()
        self.create_feeding(now - timedelta(hours=3), feed_quantity=2.0, feed_type='automatic')
        self.create_feeding(now - timedelta(hours=1), feed_quantity=2.5, feed_type='automatic')

        response = self.client.get(
            reverse('dashboardReportPreview'),
            {
                'batch_code': self.batch.batch_code,
                'start_date': timezone.localdate().isoformat(),
                'end_date': timezone.localdate().isoformat(),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        report = response.data['results']
        self.assertTrue(report['report_id'].startswith('RPT-'))
        self.assertEqual(report['batch']['code'], self.batch.batch_code)
        self.assertEqual(report['summary']['total_scheduled_feeds'], 2)
        self.assertEqual(report['summary']['enabled_feeds'], 2)
        self.assertEqual(report['summary']['disabled_feeds'], 0)
        self.assertEqual(report['summary']['total_planned_feed_kg'], 4.5)
        self.assertEqual(report['summary']['overdue_feeds'], 2)
        self.assertEqual(report['summary']['automation_rate_percent'], 100)
        self.assertEqual(report['status']['severity'], 'critical')
        self.assertTrue(report['status']['needs_review'])
        self.assertTrue(report['flags']['has_overdue'])
        self.assertTrue(report['flags']['is_fully_automated'])
        self.assertGreaterEqual(len(report['messages']), 1)

    def test_report_preview_returns_empty_summary_when_no_batch_exists(self):
        PigBatches.objects.all().delete()
        response = self.client.get(reverse('dashboardReportPreview'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        report = response.data['results']
        self.assertEqual(report['batch']['code'], None)
        self.assertEqual(report['summary']['total_scheduled_feeds'], 0)
        self.assertEqual(report['status']['severity'], 'normal')
