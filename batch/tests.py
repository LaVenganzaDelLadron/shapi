from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from batch.models import PigBatches
from growth.models import GrowthStage
from pen.models import Pen


class PigBatchCurrentAgeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.pen = Pen.objects.create(
            pen_name='API Pen',
            capacity=12,
            status='available',
            notes='test pen',
            date=timezone.now(),
        )
        self.growth_stage = GrowthStage.objects.create(
            growth_name='Grower',
            date=timezone.now(),
        )

    def test_batch_list_uses_computed_current_age(self):
        started_at = timezone.now() - timedelta(days=7)
        batch = PigBatches.objects.create(
            batch_name='API Batch',
            no_of_pigs=8,
            current_age=999,
            avg_weight=18.5,
            notes='test batch',
            pen_code=self.pen,
            growth_stage=self.growth_stage,
            date=started_at,
        )

        response = self.client.get(reverse('getAllBatches'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['data'][0]['batch_code'], batch.batch_code)
        self.assertEqual(response.data['data'][0]['current_age'], 7)
