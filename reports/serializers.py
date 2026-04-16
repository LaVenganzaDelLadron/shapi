from rest_framework import serializers

from batch.models import PigBatches


class ReportsQuerySerializer(serializers.Serializer):
    batch_code = serializers.CharField(required=False, allow_blank=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=200, default=50)

    def validate_batch_code(self, value):
        if not PigBatches.objects.filter(batch_code=value).exists():
            raise serializers.ValidationError(f'Unknown batch_code: {value}')
        return value

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError('start_date must be on or before end_date.')
        return attrs


class RecentActivityQuerySerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False, min_value=1, max_value=100, default=10)
