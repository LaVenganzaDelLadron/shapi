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


class ReportsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        now = timezone.now()

        self.pen = Pen.objects.create(
            pen_name='Reports Pen',
            capacity=10,
            status='available',
            notes='reports pen',
            date=now,
        )
        self.growth_stage = GrowthStage.objects.create(
            growth_name='Grower',
            date=now,
        )
        self.batch = PigBatches.objects.create(
            batch_name='Batch A',
            no_of_pigs=5,
            current_age=0,
            avg_weight=15.0,
            notes='reports batch',
            pen_code=self.pen,
            growth_stage=self.growth_stage,
            date=now - timedelta(days=20),
        )
        self.device = Device.objects.create(
            pen_code=self.pen,
            date=now,
        )

        # Overdue automatic feed
        Feeding.objects.create(
            feed_quantity=1.5,
            feed_time=now - timedelta(hours=4),
            repeat_days='everyday',
            feed_type='automatic',
            growth_stage=self.growth_stage,
            batch_code=self.batch,
            device_code=self.device,
            pen_code=self.pen,
            date=now - timedelta(hours=4),
        )
        # Upcoming manual feed
        Feeding.objects.create(
            feed_quantity=3.0,
            feed_time=now + timedelta(hours=4),
            repeat_days='everyday',
            feed_type='manual',
            growth_stage=self.growth_stage,
            batch_code=self.batch,
            device_code=self.device,
            pen_code=self.pen,
            date=now + timedelta(hours=4),
        )

    def test_reports_summary_route_returns_dashboard_cards_data(self):
        response = self.client.get(reverse('reportsSummary'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        results = response.data['results']
        self.assertEqual(results['reports_generated'], 1)
        self.assertEqual(results['critical_findings'], 1)
        self.assertEqual(results['enabled_feeds'], 1)
        self.assertEqual(results['total_scheduled_feeds'], 2)

    def test_reports_packets_route_returns_frontend_ready_packet_shape(self):
        response = self.client.get(reverse('reportsPackets'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        packet = response.data['results'][0]
        self.assertTrue(packet['report_id'].startswith('RPT-'))
        self.assertEqual(packet['batch']['code'], self.batch.batch_code)
        self.assertEqual(packet['summary']['total_scheduled_feeds'], 2)
        self.assertEqual(packet['summary']['enabled_feeds'], 1)
        self.assertEqual(packet['summary']['disabled_feeds'], 1)
        self.assertEqual(packet['summary']['total_planned_feed_kg'], 4.5)
        self.assertTrue(packet['status']['needs_review'])
        self.assertIn('messages', packet)
        self.assertIn('flags', packet)

    def test_reports_packet_detail_route_returns_selected_packet(self):
        packets_response = self.client.get(reverse('reportsPackets'))
        report_id = packets_response.data['results'][0]['report_id']

        response = self.client.get(reverse('reportsPacketDetail', args=[report_id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results']['report_id'], report_id)

    def test_reports_volume_trend_route_returns_series(self):
        response = self.client.get(reverse('reportsVolumeTrend'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        series = response.data['results']
        self.assertGreaterEqual(len(series), 1)
        self.assertIn('date', series[0])
        self.assertIn('total_planned_feed_kg', series[0])

    def test_reports_recent_activity_route_returns_table_rows(self):
        response = self.client.get(reverse('reportsRecentActivity'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data['results']
        self.assertGreaterEqual(len(rows), 1)
        self.assertTrue(rows[0]['report_id'].startswith('RPT-'))
        self.assertIn('owner', rows[0])
        self.assertIn('status', rows[0])
