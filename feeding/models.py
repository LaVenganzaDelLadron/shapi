from django.db import models



class Feeding(models.Model):
    feed_code = models.CharField(max_length=120, unique=True)
    feed_quantity = models.FloatField()
    feed_time = models.DateTimeField()
    growth_stage = models.ForeignKey('growth.GrowthStage',on_delete=models.CASCADE)
    batch_code = models.ForeignKey('batch.PigBatches', on_delete=models.CASCADE)
    device_code = models.ForeignKey('device.Device', on_delete=models.CASCADE)
    pen_code = models.ForeignKey('pen.Pen', on_delete=models.CASCADE)
    date = models.DateTimeField()



    def __str__(self):
        return f"{self.feed_code} {self.feed_quantity} {self.feed_type}"
