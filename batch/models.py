from django.db import models

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

    def __str__(self):
        return f'{self.batch_code} {self.batch_name}'
