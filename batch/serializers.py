from rest_framework import serializers
from growth.models import GrowthStage
from pen.models import Pen
from batch.models import PigBatches


class PigBatchesSerializer(serializers.ModelSerializer):
    pen_code_id = serializers.SlugRelatedField(
        source='pen_code',
        slug_field='pen_code',
        queryset=Pen.objects.all(),
    )
    growth_stage_id = serializers.SlugRelatedField(
        source='growth_stage',
        slug_field='growth_code',
        queryset=GrowthStage.objects.all(),
    )

    class Meta:
        model = PigBatches
        fields = (
            'batch_code',
            'batch_name',
            'no_of_pigs',
            'current_age',
            'avg_weight',
            'notes',
            'pen_code_id',
            'growth_stage_id',
            'date',
        )



