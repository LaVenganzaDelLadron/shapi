from rest_framework import serializers

from batch.age import calculate_batch_age, utc_date
from batch.models import PigBatches
from growth.models import GrowthStage
from record.models import Record

class RecordSerializer(serializers.ModelSerializer):
    batch_code = serializers.SlugRelatedField(
        slug_field='batch_code',
        queryset=PigBatches.objects.all(),
    )
    growth_stage = serializers.SlugRelatedField(
        slug_field='growth_code',
        queryset=GrowthStage.objects.all(),
    )
    pig_age_days = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Record
        fields = ('record_code', 'batch_code', 'pig_age_days', 'avg_weight', 'growth_stage', 'date')
        extra_kwargs = {
            'record_code': {'read_only': True},
        }

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        batch_code = attrs.get('batch_code', getattr(instance, 'batch_code', None))
        avg_weight = attrs.get('avg_weight', getattr(instance, 'avg_weight', None))
        growth_stage = attrs.get('growth_stage', getattr(instance, 'growth_stage', None))
        date = attrs.get('date', getattr(instance, 'date', None))
        snapshot_day = utc_date(date) if date else None

        if batch_code and date:
            attrs['pig_age_days'] = calculate_batch_age(batch_code.date, as_of=date)

        duplicate_record = Record.objects.none()
        if batch_code and snapshot_day is not None:
            duplicate_record = Record.objects.filter(
                batch_code=batch_code,
                date__date=snapshot_day,
            )

        if instance is not None:
            duplicate_record = duplicate_record.exclude(pk=instance.pk)

        if duplicate_record.exists():
            raise serializers.ValidationError(
                {'message': 'A daily snapshot already exists for this batch on this UTC day.'}
            )

        if batch_code and date and avg_weight is None:
            raise serializers.ValidationError({'avg_weight': 'This field is required.'})

        if batch_code and date and growth_stage is None:
            raise serializers.ValidationError({'growth_stage': 'This field is required.'})

        return attrs
