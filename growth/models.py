from django.db import models

class GrowthStage(models.Model):
    growth_code = models.CharField(max_length=120, unique=True)
    growth_name = models.CharField(max_length=120, unique=True)
    date = models.DateTimeField()

    @classmethod
    def generate_growth_code(cls):
        prefix = 'GROWTH-'





    def __str__(self):
        return f'{self.growth_code} {self.growth_name}'