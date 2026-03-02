from django.db import models
import re

class PigBatches(models.Model):
    batch_code = models.CharField(max_length=120, unique=True)
    batch_name = models.CharField(max_length=120, unique=True)
    no_of_pigs = models.IntegerField()
    current_age = models.IntegerField()
    avg_weight = models.FloatField()
    notes = models.CharField(max_length=120)
    pen_code = models.ForeignKey('pen.Pen', on_delete=models.CASCADE, related_name='batches')
    growth_stage = models.ForeignKey('growth.GrowthStage', on_delete=models.CASCADE, related_name='batches')
    date = models.DateTimeField()

    @classmethod
    def generate_next_batch_code(cls):
        prefix = 'BATCH'
        pattern = re.compile(rf'^{prefix}(\d+)$')
        max_number = 0

        codes = cls.objects.filter(batch_code__startswith=prefix).values_list('batch_code', flat=True)
        for code in codes:
            match = pattern.match(code)
            if match:
                max_number = max(max_number, int(match.group(1)))

        return f'{prefix}{max_number + 1:03d}'

    def save(self, *args, **kwargs):
        if not self.batch_code:
            self.batch_code = self.generate_next_batch_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.batch_code} {self.batch_name}'
