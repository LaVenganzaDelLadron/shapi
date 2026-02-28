import re

from django.db import models

class GrowthStage(models.Model):
    growth_code = models.CharField(max_length=120, unique=True)
    growth_name = models.CharField(max_length=120, unique=True)
    date = models.DateTimeField()

    @classmethod
    def generate_growth_code(cls):
        prefix = 'GROWTH'
        pattern = re.compile(rf'^{prefix}(\d+)$')
        max_number = 0
        
        codes = cls.objects.filter(growth_code__startswith=pattern).values_list('growth_code', flat=True)
        for code in codes:
            match = pattern.match(code)
            if match:
                max_number = max(max_number, int(match.group(1)))
                
        return f'{prefix}{max_number + 1:03d}'

    def save(self, *args, **kwargs):
        if not self.growth_code:
            self.growth_code = self.generate_growth_code()
        super().save(*args, **kwargs)


    def __str__(self):
        return f'{self.growth_code} {self.growth_name}'