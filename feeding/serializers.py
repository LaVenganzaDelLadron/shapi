import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from feeding.models import Feeding
from batch.models import PigBatches
from device.models import Device
from pen.models import Pen
from growth.models import GrowthStage

logger = logging.getLogger(__name__)


class LenientSlugRelatedField(serializers.SlugRelatedField):
    """Accepts unknown slug values and returns the raw string for auto-creation."""

    def to_internal_value(self, data):
        if data is None:
            if self.allow_null:
                return None
            self.fail('required')
        if isinstance(data, str) and data.strip() == '':
            if self.allow_null:
                return None
            self.fail('required')

        try:
            return super().to_internal_value(data)
        except serializers.ValidationError:
            return str(data)


class FeedingSerializer(serializers.ModelSerializer):
    repeat_days = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    growth_code = LenientSlugRelatedField(
        source='growth_stage',
        slug_field='growth_code',
        queryset=GrowthStage.objects.all(),
    )
    batch_code = LenientSlugRelatedField(
        slug_field='batch_code',
        queryset=PigBatches.objects.all(),
    )
    device_code = LenientSlugRelatedField(
        slug_field='device_code',
        queryset=Device.objects.all(),
    )
    pen_code = LenientSlugRelatedField(
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

    def _resolve_pen(self, value):
        if isinstance(value, Pen):
            return value

        code = str(value or '').strip()
        if code == '':
            code = 'PEN-AUTO'

        pen, created = Pen.objects.get_or_create(
            pen_code=code,
            defaults={
                'pen_name': f'Auto {code}',
                'capacity': 0,
                'status': 'available',
                'notes': 'Auto-created by feeding',
                'date': timezone.now(),
            },
        )

        if created:
            logger.info('Auto-created pen', extra={'pen_code': code})

        return pen

    def _resolve_growth(self, value):
        if isinstance(value, GrowthStage):
            return value

        code = str(value or '').strip()
        if code == '':
            code = 'GROWTH-AUTO'

        growth, created = GrowthStage.objects.get_or_create(
            growth_code=code,
            defaults={
                'growth_name': f'Auto {code}',
                'date': timezone.now(),
            },
        )

        if created:
            logger.info('Auto-created growth stage', extra={'growth_code': code})

        return growth

    def _resolve_batch(self, value, pen: Pen, growth: GrowthStage):
        if isinstance(value, PigBatches):
            return value

        code = str(value or '').strip()
        if code == '':
            code = 'BATCH-AUTO'

        batch, created = PigBatches.objects.get_or_create(
            batch_code=code,
            defaults={
                'batch_name': f'Auto {code}',
                'no_of_pigs': 0,
                'current_age': 0,
                'avg_weight': 0,
                'notes': 'Auto-created by feeding',
                'pen_code': pen,
                'growth_stage': growth,
                'date': timezone.now(),
            },
        )

        if created:
            logger.info('Auto-created batch', extra={'batch_code': code})

        return batch

    def _resolve_device(self, value, pen: Pen):
        if isinstance(value, Device):
            return value

        code = str(value or '').strip()
        if code == '':
            code = 'DEV-AUTO'

        device, created = Device.objects.get_or_create(
            device_code=code,
            defaults={
                'pen_code': pen,
                'date': timezone.now(),
            },
        )

        if created:
            logger.info('Auto-created device', extra={'device_code': code})

        return device

    @transaction.atomic
    def create(self, validated_data):
        pen_value = validated_data.pop('pen_code', None)
        growth_value = validated_data.pop('growth_stage', None)
        batch_value = validated_data.pop('batch_code', None)
        device_value = validated_data.pop('device_code', None)

        pen = self._resolve_pen(pen_value)
        growth = self._resolve_growth(growth_value)
        batch = self._resolve_batch(batch_value, pen, growth)
        device = self._resolve_device(device_value, pen)

        validated_data['pen_code'] = pen
        validated_data['growth_stage'] = growth
        validated_data['batch_code'] = batch
        validated_data['device_code'] = device

        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        if 'pen_code' in validated_data:
            validated_data['pen_code'] = self._resolve_pen(validated_data.get('pen_code'))

        if 'growth_stage' in validated_data:
            validated_data['growth_stage'] = self._resolve_growth(validated_data.get('growth_stage'))

        if 'batch_code' in validated_data:
            pen = validated_data.get('pen_code', instance.pen_code)
            growth = validated_data.get('growth_stage', instance.growth_stage)
            validated_data['batch_code'] = self._resolve_batch(validated_data.get('batch_code'), pen, growth)

        if 'device_code' in validated_data:
            pen = validated_data.get('pen_code', instance.pen_code)
            validated_data['device_code'] = self._resolve_device(validated_data.get('device_code'), pen)

        return super().update(instance, validated_data)
