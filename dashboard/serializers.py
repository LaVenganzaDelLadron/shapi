from rest_framework import serializers


class GrowthTrendsQuerySerializer(serializers.Serializer):
    batch_code = serializers.CharField(required=False, allow_blank=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError('start_date must be on or before end_date.')
        return attrs


class FeedConsumptionQuerySerializer(GrowthTrendsQuerySerializer):
    group_by = serializers.ChoiceField(choices=['day', 'week', 'none'], required=False, default='none')


class NextFeedingScheduleQuerySerializer(serializers.Serializer):
    batch_code = serializers.CharField(required=False, allow_blank=False)


class FeedDispensedTodayQuerySerializer(serializers.Serializer):
    batch_code = serializers.CharField(required=False, allow_blank=False)
    per_batch = serializers.BooleanField(required=False, default=False)

