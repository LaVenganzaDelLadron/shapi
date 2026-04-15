from rest_framework import serializers

from batch.age import calculate_batch_age
from batch.models import PigBatches
from growth.models import GrowthStage
from pen.models import Pen


class PigBatchesSerializer(serializers.ModelSerializer):
    current_age = serializers.SerializerMethodField()
    pen_code = serializers.CharField(source='pen_code.pen_code', read_only=True)
    growth_stage = serializers.CharField(source='growth_stage.growth_code', read_only=True)
    pen_code_id = serializers.SlugRelatedField(
        source='pen_code',
        slug_field='pen_code',
        queryset=Pen.objects.all(),
        write_only=True,
    )
    growth_stage_id = serializers.SlugRelatedField(
        source='growth_stage',
        slug_field='growth_code',
        queryset=GrowthStage.objects.all(),
        write_only=True,
    )
    no_of_pigs = serializers.IntegerField(min_value=0)
    avg_weight = serializers.FloatField(min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = PigBatches
        fields = (
            'batch_code',
            'batch_name',
            'no_of_pigs',
            'current_age',
            'avg_weight',
            'notes',
            'pen_code',
            'pen_code_id',
            'growth_stage',
            'growth_stage_id',
            'date',
        )
        extra_kwargs = {
            'batch_code': {'read_only': True},
        }

    def get_current_age(self, instance):
        return instance.get_current_age()

    def create(self, validated_data):
        validated_data['current_age'] = calculate_batch_age(validated_data['date'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data['current_age'] = calculate_batch_age(validated_data.get('date', instance.date))
        return super().update(instance, validated_data)

    def validate_batch_name(self, value):
        batch_name = value.strip()
        if not batch_name:
            raise serializers.ValidationError('batch_name is required.')
        return batch_name
