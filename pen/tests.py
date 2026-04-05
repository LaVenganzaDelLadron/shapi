from django.test import TestCase

from batch.models import PigBatches
from growth.models import GrowthStage
from pen.models import Pen
from pen.services import sync_pen_statuses


class PenStatusSyncTests(TestCase):
    def setUp(self):
        self.growth_stage = GrowthStage.objects.create(
            growth_name='Grower',
            date='2026-04-05T08:00:00Z',
        )

    def create_pen(self, name, capacity, status='available'):
        return Pen.objects.create(
            pen_name=name,
            capacity=capacity,
            status=status,
            notes='test pen',
            date='2026-04-05T08:00:00Z',
        )

    def create_batch(self, name, pigs, pen):
        return PigBatches.objects.create(
            batch_name=name,
            no_of_pigs=pigs,
            current_age=30,
            avg_weight=14.5,
            notes='test batch',
            pen_code=pen,
            growth_stage=self.growth_stage,
            date='2026-04-05T08:00:00Z',
        )

    def test_sync_marks_pen_occupied_when_total_pigs_meet_capacity(self):
        pen = self.create_pen('Pen A', capacity=5)

        self.create_batch('Batch A', pigs=5, pen=pen)

        pen.refresh_from_db()
        self.assertEqual(pen.status, 'occupied')

    def test_sync_keeps_pen_available_when_total_pigs_are_below_capacity(self):
        pen = self.create_pen('Pen B', capacity=9)

        self.create_batch('Batch B', pigs=5, pen=pen)

        pen.refresh_from_db()
        self.assertEqual(pen.status, 'available')

    def test_sync_uses_the_sum_of_all_batches_for_the_same_pen(self):
        pen = self.create_pen('Pen C', capacity=9)

        self.create_batch('Batch C1', pigs=4, pen=pen)
        self.create_batch('Batch C2', pigs=5, pen=pen)

        pen.refresh_from_db()
        self.assertEqual(pen.status, 'occupied')

    def test_sync_updates_both_old_and_new_pens_when_a_batch_moves(self):
        old_pen = self.create_pen('Pen D', capacity=5)
        new_pen = self.create_pen('Pen E', capacity=4)
        batch = self.create_batch('Batch D', pigs=5, pen=old_pen)

        batch.pen_code = new_pen
        batch.save()

        old_pen.refresh_from_db()
        new_pen.refresh_from_db()
        self.assertEqual(old_pen.status, 'available')
        self.assertEqual(new_pen.status, 'occupied')

    def test_sync_recomputes_all_pens_in_one_pass(self):
        full_pen = self.create_pen('Pen F', capacity=4, status='available')
        open_pen = self.create_pen('Pen G', capacity=7, status='occupied')

        self.create_batch('Batch F', pigs=4, pen=full_pen)
        self.create_batch('Batch G', pigs=3, pen=open_pen)

        Pen.objects.filter(pk=full_pen.pk).update(status='available')
        Pen.objects.filter(pk=open_pen.pk).update(status='occupied')

        updated_count = sync_pen_statuses()

        full_pen.refresh_from_db()
        open_pen.refresh_from_db()
        self.assertEqual(updated_count, 2)
        self.assertEqual(full_pen.status, 'occupied')
        self.assertEqual(open_pen.status, 'available')
