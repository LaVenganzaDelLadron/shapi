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
