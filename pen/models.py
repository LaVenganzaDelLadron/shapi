from django.db import models
import re


class Pen(models.Model):
    pen_status = [
        ('available', 'available'),
        ('occupied', 'Occupied'),
    ]

    pen_code = models.CharField(max_length=120,unique=True)
    pen_name = models.CharField(max_length=120,unique=True)
    capacity = models.IntegerField()
    status = models.CharField(max_length=120, choices=pen_status, default='available')
    notes = models.CharField(max_length=120)
    date = models.DateTimeField()

    @classmethod
    def generate_next_pen_code(cls):
        prefix = 'PEN-'
        pattern = re.compile(rf'^{prefix}(\d+)$')
        max_number = 0

        codes = cls.objects.filter(pen_code__startswith=prefix).values_list('pen_code', flat=True)
        for code in codes:
            match = pattern.match(code)
            if match:
                max_number = max(max_number, int(match.group(1)))

        return f'{prefix}{max_number + 1:03d}'

    def save(self, *args, **kwargs):
        if not self.pen_code:
            self.pen_code = self.generate_next_pen_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.pen_code} {self.pen_name}'
