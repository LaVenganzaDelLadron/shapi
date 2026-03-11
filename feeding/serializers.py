from rest_framework import serializers
from feeding.models import Feeding
from batch.models import PigBatches
from device.models import Device
from pen.models import Pen
from growth.models import GrowthStage


class FeedingSerializer(serializers.ModelSerializer):
    repeat_days = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    growth_code = serializers.SlugRelatedField(
        source='growth_stage',
        slug_field='growth_code',
        queryset=GrowthStage.objects.all(),
    )
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
            'repeat_days',
            'feed_type',
            'growth_code',
            'batch_code',
            'device_code',
            'pen_code',
            'date',
        )

    def validate_repeat_days(self, value):
        if value is None:
            return None

        cleaned = value.strip().lower()
        if cleaned == '':
            return None
        if cleaned == 'everyday':
            return 'everyday'

        allowed_days = {
            'sunday',
            'monday',
            'tuesday',
            'wednesday',
            'thursday',
            'friday',
            'saturday',
        }
        parts = [part.strip().lower() for part in cleaned.split(',') if part.strip()]
        if not parts:
            raise serializers.ValidationError(
                'repeat_days must be "everyday" or a comma-separated list of weekdays.'
            )

        invalid_days = [day for day in parts if day not in allowed_days]
        if invalid_days:
            raise serializers.ValidationError(
                'Invalid repeat_days values: ' + ', '.join(sorted(set(invalid_days)))
            )

        seen = set()
        normalized = []
        for day in parts:
            if day not in seen:
                normalized.append(day)
                seen.add(day)
        return ','.join(normalized)
