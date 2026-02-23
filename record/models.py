from django.db import models

class Record(models.Model):
    record_code = models.CharField(max_length=120, unique=True)
    batch_code = models.ForeignKey('batch.PigBatches', on_delete=models.CASCADE)
    pig_age_days = models.IntegerField()
    avg_weight = models.FloatField()
    growth_stage = models.ForeignKey('growth.GrowthStage', on_delete=models.CASCADE)
    date = models.DateTimeField()

    def __str__(self):
        return f'{self.record_code} {self.batch_code}'


