from django.db import models
import re


class Datamining(models.Model):
    pen_status = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    datamining_code = models.CharField(max_length=120)
    pig_age_days = models.CharField(max_length=120)
    avg_weight = models.CharField(max_length=120)
    feed_quantity = models.CharField(max_length=120)
    number_of_feeding_per_day = models.IntegerField()
    feeding_interval = models.IntegerField()
    pen_capacity = models.FloatField()
    status = models.CharField(max_length=120, choices=pen_status, default='available')
    growth_stage = models.CharField(max_length=120)
    feed_type = models.CharField(max_length=120)
    device_code = models.CharField(max_length=120)
    repeat_days = models.CharField(max_length=120)
    notes = models.DateTimeField()


    @classmethod
    def generate_next_datamining_code(cls):
        prefix = 'DM'
        pattern = re.compile(rf'^{prefix}(\d+)$')
        max_number = 0

        codes = cls.objects.filter(datamining__startswith=prefix).values_list('datamining', flat=True)
        for code in codes:
            match = pattern.match(code)
            if match:
                max_number = max(max_number, int(match.group(1)))

        return f'{prefix}{max_number + 1:03d}'
    
    def save(self, *args, **kwargs):
        if not self.datamining_code:
            self.datamining_code = self.generate_next_datamining_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.datamining_code} {self.pig_age_days} days'









