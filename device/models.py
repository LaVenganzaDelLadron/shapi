from django.db import models
import re


class Device(models.Model):
    device_code = models.CharField(max_length=120, unique=True)
    pen_code = models.ForeignKey('pen.Pen', on_delete=models.CASCADE, related_name='devices')
    date = models.DateTimeField()


    @classmethod
    def generate_next_batch_code(cls):
        prefix = 'BATCH'
        pattern = re.compile(rf'^{prefix}(\d+)$')
        max_number = 0

        codes = cls.objects.filter(pen_code__startswith=prefix).values_list('batch_code', flat=True)
        for code in codes:
            match = pattern.match(code)
            if match:
                max_number = max(max_number, int(match.group(1)))

        return f'{prefix}{max_number + 1:03d}'
        
    def save(self, *args, **kwargs):
        if not self.pen_code:
            self.pen_code = self.generate_next_batch_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.device_code}'

