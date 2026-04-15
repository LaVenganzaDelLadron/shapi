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

    def test_batch_crud_flow(self):
        started_at = timezone.now() - timedelta(days=10)
        create_response = self.client.post(
            '/batch/add/',
            {
                'batch_name': 'New Batch',
                'no_of_pigs': 12,
                'avg_weight': 22.5,
                'notes': 'healthy batch',
                'pen_code': self.pen.pen_code,
                'growth_stage': self.growth_stage.growth_code,
                'date': started_at.isoformat(),
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data['message'], 'Batch created successfully')
        batch_code = create_response.data['data']['batch_code']
        self.assertEqual(create_response.data['data']['pen_code'], self.pen.pen_code)
        self.assertEqual(create_response.data['data']['growth_stage'], self.growth_stage.growth_code)

        list_response = self.client.get('/batch/all/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)

        update_response = self.client.put(
            f'/batch/update/{batch_code}/',
            {
                'batch_name': 'Updated Batch',
                'no_of_pigs': 10,
                'avg_weight': 24.0,
                'notes': 'updated notes',
                'pen_code': self.pen.pen_code,
                'growth_stage': self.growth_stage.growth_code,
                'date': started_at.isoformat(),
            },
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['data']['batch_name'], 'Updated Batch')

        delete_response = self.client.delete(f'/batch/delete/{batch_code}/')
        self.assertEqual(delete_response.status_code, status.HTTP_200_OK)
        self.assertEqual(delete_response.data['batch_code'], batch_code)
        self.assertFalse(PigBatches.objects.filter(batch_code=batch_code).exists())
