from rest_framework import serializers
from record.models import Record
from batch.models import PigBatches
from growth.models import GrowthStage

class RecordSerializer(serializers.ModelSerializer):
    batch_code = serializers.SlugRelatedField(
        slug_field='batch_code',
        queryset=PigBatches.objects.all(),
    )
    growth_stage = serializers.SlugRelatedField(
        slug_field='growth_code',
        queryset=GrowthStage.objects.all(),
    )
    
    class Meta:
        model = Record
        fields = ('record_code', 'batch_code', 'pig_age_days', 'avg_weight', 'growth_stage', 'date')
        extra_kwargs = {
            'record_code': {'read_only': True},
        }

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        batch_code = attrs.get('batch_code', getattr(instance, 'batch_code', None))
        pig_age_days = attrs.get('pig_age_days', getattr(instance, 'pig_age_days', None))
        avg_weight = attrs.get('avg_weight', getattr(instance, 'avg_weight', None))
        growth_stage = attrs.get('growth_stage', getattr(instance, 'growth_stage', None))
        date = attrs.get('date', getattr(instance, 'date', None))

        duplicate_record = Record.objects.filter(
            batch_code=batch_code,
            pig_age_days=pig_age_days,
            avg_weight=avg_weight,
            growth_stage=growth_stage,
            date=date,
        )

        if instance is not None:
            duplicate_record = duplicate_record.exclude(pk=instance.pk)

        if duplicate_record.exists():
            raise serializers.ValidationError(
                {'message': 'Record already exists.'}
            )

        return attrs
