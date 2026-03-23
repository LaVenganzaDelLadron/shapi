from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from batch.models import PigBatches
from growth.models import GrowthStage
from pen.models import Pen
from record.models import Record


class RecordControllerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.pen = Pen.objects.create(
            pen_name='North Pen',
            capacity=20,
            status='available',
            notes='test pen',
            date='2026-03-23T08:00:00Z',
        )
        self.growth_stage = GrowthStage.objects.create(
            growth_name='Grower',
            date='2026-03-23T08:00:00Z',
        )
        self.batch = PigBatches.objects.create(
            batch_name='Batch Alpha',
            no_of_pigs=10,
            current_age=45,
            avg_weight=22.5,
            notes='test batch',
            pen_code=self.pen,
            growth_stage=self.growth_stage,
            date='2026-03-23T08:00:00Z',
        )

    def test_post_duplicate_record_returns_already_exists(self):
        payload = {
            'batch_code': self.batch.batch_code,
            'pig_age_days': 45,
            'avg_weight': 22.5,
            'growth_stage': self.growth_stage.growth_code,
            'date': '2026-03-23T09:00:00Z',
        }

        first_response = self.client.post(reverse('addRecord'), payload, format='json')
        second_response = self.client.post(reverse('addRecord'), payload, format='json')

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(second_response.data, {'message': 'Record already exists.'})
        self.assertEqual(Record.objects.count(), 1)
