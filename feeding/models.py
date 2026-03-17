from django.db import models
import re



class Feeding(models.Model):
    feed_type_choices = [
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
        ('override', 'Override'),
        ('emergency', 'Emergency'),
        ('test', 'Test'),
    ]

    feed_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    feed_quantity = models.FloatField()
    feed_time = models.DateTimeField()
    repeat_days = models.CharField(max_length=120, blank=True, null=True)
    feed_type = models.CharField(max_length=20, choices=feed_type_choices)
    growth_stage = models.ForeignKey('growth.GrowthStage',on_delete=models.CASCADE)
    batch_code = models.ForeignKey('batch.PigBatches', on_delete=models.CASCADE)
    device_code = models.ForeignKey('device.Device', on_delete=models.CASCADE)
    pen_code = models.ForeignKey('pen.Pen', on_delete=models.CASCADE)
    date = models.DateTimeField()

    @classmethod
    def generate_next_feed_code(cls):
        prefix = 'FEED'
        pattern = re.compile(rf'^{prefix}(\d+)$')
        max_number = 0

        codes = cls.objects.filter(feed_code__startswith=prefix).values_list('feed_code', flat=True)
        for code in codes:
            match = pattern.match(code)
            if match:
                max_number = max(max_number, int(match.group(1)))

        return f'{prefix}{max_number + 1:03d}'

    def save(self, *args, **kwargs):
        if not self.feed_code:
            self.feed_code = self.generate_next_feed_code()
        super().save(*args, **kwargs)



    def __str__(self):
        return f"{self.feed_code} {self.feed_quantity} {self.feed_type}"
