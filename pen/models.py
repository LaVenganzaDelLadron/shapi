from django.db import models


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

    def __str__(self):
        return f'{self.pen_code} {self.pen_name}'
