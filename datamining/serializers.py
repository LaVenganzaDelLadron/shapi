from rest_framework import serializers

from datamining.models import PigMLData


class PigMLDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PigMLData
        fields = (
            'record_code',
            'batch_code',
            'pen_code',
            'sample_date',
            'pig_age_days',
            'avg_weight',
            'total_feed_quantity',
            'feeding_count',
            'avg_feeding_interval_hours',
            'pen_capacity',
            'pen_status',
            'growth_stage',
            'feed_type_mode',
            'device_code',
            'window_days',
            'created_at',
            'updated_at',
        )


class PredictWeightSerializer(serializers.Serializer):
    pig_age_days = serializers.IntegerField(min_value=1)
    total_feed_quantity = serializers.FloatField(min_value=0)
    feeding_count = serializers.IntegerField(min_value=1)
    avg_feeding_interval_hours = serializers.FloatField(min_value=0)


class ClassifyRiskSerializer(serializers.Serializer):
    pig_age_days = serializers.IntegerField(min_value=1)
    avg_weight = serializers.FloatField(min_value=0)
    feeding_count = serializers.IntegerField(min_value=1)
    total_feed_quantity = serializers.FloatField(min_value=0)


class SuggestFeedingSerializer(serializers.Serializer):
    current_weight = serializers.FloatField(min_value=0)
    target_weight = serializers.FloatField(min_value=0)
    pig_age_days = serializers.IntegerField(min_value=1)
