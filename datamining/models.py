from django.db import models


class PigMLData(models.Model):
    record = models.OneToOneField(
        'record.Record',
        on_delete=models.CASCADE,
        related_name='pig_ml_data',
    )
    record_code = models.CharField(max_length=120, unique=True)
    batch_code = models.CharField(max_length=120)
    pen_code = models.CharField(max_length=120)
    sample_date = models.DateTimeField()
    pig_age_days = models.IntegerField()
    avg_weight = models.FloatField()
    total_feed_quantity = models.FloatField(default=0)
    feeding_count = models.IntegerField(default=0)
    avg_feeding_interval_hours = models.FloatField(default=0)
    pen_capacity = models.IntegerField()
    pen_status = models.CharField(max_length=120)
    growth_stage = models.CharField(max_length=120)
    feed_type_mode = models.CharField(max_length=20, blank=True)
    device_code = models.CharField(max_length=120, blank=True)
    window_days = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sample_date', 'record_code']

    def __str__(self):
        return f'{self.record_code} {self.avg_weight}'
