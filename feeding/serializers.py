from rest_framework import serializers
from feeding.models import Feeding
from batch.models import PigBatches
from device.models import Device
from pen.models import Pen


class FeedingSerializer(serializers.ModelSerializer):
    batch_code = serializers.SlugRelatedField(
        slug_field='batch_code',
        queryset=PigBatches.objects.all(),
    )
    device_code = serializers.SlugRelatedField(
        slug_field='device_code',
        queryset=Device.objects.all(),
    )
    pen_code = serializers.SlugRelatedField(
        slug_field='pen_code',
        queryset=Pen.objects.all(),
    )

    class Meta:
        model = Feeding
        fields = (
            'feed_code',
            'feed_quantity',
            'feed_time',
            'feed_type',
            'batch_code',
            'device_code',
            'pen_code',
            'date',
        )
