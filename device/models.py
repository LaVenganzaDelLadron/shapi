from django.db import models


class Device(models.Model):
    device_code = models.CharField(max_length=120, unique=True)
    device_type = models.CharField(max_length=120)
    pen_code = models.ForeignKey('pen.Pen', on_delete=models.CASCADE, related_name='devices')
    date = models.DateTimeField()

    def __str__(self):
        return f'{self.device_code} {self.device_type}'


