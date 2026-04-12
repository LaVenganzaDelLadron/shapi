import re

from django.db import IntegrityError, models, transaction
from django.db.models.functions import TruncDate

class Record(models.Model):
    record_code = models.CharField(max_length=120, unique=True)
    batch_code = models.ForeignKey('batch.PigBatches', on_delete=models.CASCADE)
    pig_age_days = models.IntegerField()
    avg_weight = models.FloatField()
    growth_stage = models.ForeignKey('growth.GrowthStage', on_delete=models.CASCADE)
    date = models.DateTimeField()

    class Meta:
        ordering = ['date', 'record_code']
        constraints = [
            models.UniqueConstraint(
                'batch_code',
                TruncDate('date'),
                name='unique_record_batch_per_utc_day',
            ),
        ]

    @classmethod
    def generate_next_record_code(cls):
        prefix = 'REC'
        pattern = re.compile(rf'^{prefix}(\d+)$')
        max_number = 0

        codes = cls.objects.filter(record_code__startswith=prefix).values_list('record_code', flat=True)
        for code in codes:
            match = pattern.match(code)
            if match:
                max_number = max(max_number, int(match.group(1)))

        return f'{prefix}{max_number + 1:03d}'

    def save(self, *args, **kwargs):
        if self.record_code:
            return super().save(*args, **kwargs)

        while True:
            self.record_code = self.generate_next_record_code()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                # Retry if another request claimed the same next code first.
                self.record_code = None

    def __str__(self):
        return f'{self.record_code} {self.batch_code}'
