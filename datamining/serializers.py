from rest_framework import serializers
from datamining.models import DataMining

class DataMiningSerializer(serializers.ModelSerializer):
    status = serializers.CharField()

    class Meta:
        model = DataMining
        fields = ('datamining_code', 'pig_age_days', 'avg_weight', 'feed_quantity', 'number_of_feeding_per_day',
                  'feeding_interval', 'pen_capacity', 'pen_status', 'growth_stage', 'feed_type',
                  'device_code', 'repeat_days', 'notes')
        extra_kwargs = {
            'datamining_code': {'read_only': True},
        }

    def create(self, validated_data):
        return DataMining.objects.create(**validated_data)
    
    def validate_pen_status(self, value):
        normalized = value.lower().strip()
        allowed_statuses = {choice[0] for choice in DataMining.pen_status}
        if normalized not in allowed_statuses:
            raise serializers.ValidationError(
                f"Invalid pen status '{value}'. Allowed values: {', '.join(sorted(allowed_statuses))}."
            )
        return normalized